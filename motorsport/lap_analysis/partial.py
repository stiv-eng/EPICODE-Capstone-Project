"""Conservative recovery of disjoint observed spatial/time intervals."""
import numpy as np

from .alignment import TimeMap


class RegionalTimeMap:
    """Inverse clocks only inside witnessed runs; holes return NaN, never bridges."""
    def __init__(self,runs,length,duration):
        self.runs=runs
        self.length=float(length)
        self.duration=float(duration)

    def at(self,s):
        query=np.asarray(s,float)
        value=np.full(query.shape,np.nan)
        for run in self.runs:
            mask=(query>=run['start_s_m']-1e-9)&(query<=run['end_s_m']+1e-9)
            value=np.where(mask,run['t0']+run['mapping'].at(query-run['s0']),value)
        return float(value) if value.ndim==0 else value

    def supports(self,start,end):
        return bool(np.isfinite([start,end]).all() and start<=end and
                    any(start>=r['start_s_m']-1e-9 and end<=r['end_s_m']+1e-9 for r in self.runs))

    def supports_time(self,start,end):
        if not np.isfinite([start,end]).all() or start>end:
            return False
        if end>self.duration:
            if start>=self.duration:
                return self.supports_time(start-self.duration,end-self.duration)
            return self.supports_time(start,self.duration) and self.supports_time(0.,end-self.duration)
        return any(start>=r['start_time_s']-1e-9 and end<=r['end_time_s']+1e-9 for r in self.runs)


def recover(lap,geometry,config,ambiguous,allow_boundaries=True):
    """Reacquire only a unique forward geometric match, then confirm local motion.

    The existing projection neighborhood and thresholds are retained. A restart
    needs >=3 consecutive observations advancing >=2 spatial grid cells. Repeated
    source visits cannot overlap earlier trustworthy progress. A grid cell at each
    internal run boundary is reserved for uncertain transitions, not timed sections.
    """
    xy=lap.frame[['pos_x','pos_y']].to_numpy(float)
    t=np.minimum(lap.frame.lap_elapsed_s.to_numpy(float),lap.duration_s)
    n=len(t);points=geometry.xy;length=geometry.length_m;count=len(points);h=length/count
    vectors=np.roll(points,-1,axis=0)-points;vv=np.sum(vectors*vectors,axis=1)
    finite=np.isfinite(xy).all(axis=1)
    steps=np.linalg.norm(np.diff(xy,axis=0),axis=1)
    source_jump=np.r_[False,steps>geometry.config.maximum_source_step_m]
    clock_gap=np.r_[False,np.diff(t)>config.max_clock_gap_s]
    back=int(np.ceil(config.reverse_tolerance_m/h))+3
    ahead=max(8,int(np.ceil(100./h)))
    progress=np.full(n,np.nan);offsets=np.full(n,np.nan)
    runs=[];active=None;pending=[];previous=0.;highwater=0.
    last_trusted=None;travel=0.

    def project(p,global_search=False):
        absolute=np.arange(count) if global_search else np.arange(int(np.floor(previous/h))-back,int(np.floor(previous/h))+ahead+1)
        indexes=absolute%count;v=vectors[indexes]
        u=np.clip(np.sum((p-points[indexes])*v,axis=1)/np.maximum(vv[indexes],1e-12),0.,1.)
        distances=np.linalg.norm(p-(points[indexes]+u[:,None]*v),axis=1)
        j=int(np.argmin(distances));s=float((absolute[j]+u[j])*h)
        unique=not ambiguous[indexes[j]]
        if global_search:
            separation=np.abs((absolute+u)*h-s)
            separation=np.minimum(separation,length-separation)
            unique=unique and not np.any((separation>config.ambiguous_separation_m)&
                (distances<=distances[j]+config.ambiguous_distance_m))
        return s,float(distances[j]),unique

    for i,p in enumerate(xy):
        if i and np.isfinite(steps[i-1]) and not source_jump[i]:
            travel+=float(steps[i-1])
        if not finite[i] or source_jump[i] or clock_gap[i]:
            active=None;pending=[]
            continue
        s,d,unique=project(p,active is None)
        offsets[i]=d
        if active is not None:
            good=(unique and d<=config.max_offset_m and highwater-s<=config.reverse_tolerance_m and
                  -.001<=s<=length+config.boundary_margin_m)
            if i:
                good=good and s-previous<=max(5.,2*steps[i-1]+2.)
            if good:
                progress[i]=max(highwater,s);highwater=max(highwater,s);previous=s
                active.append(i);last_trusted=i;travel=0.
                continue
            active=None;pending=[]
            s,d,unique=project(p,True)
            offsets[i]=d
        # A global restart must not jump to a different nearby track branch,
        # revisit earlier progress, or outrun the observed path across the gap.
        good=unique and d<=config.max_offset_m and 0.<=s<=length
        if last_trusted is not None:
            good=good and s>highwater+h and s-highwater<=max(5.,2*travel+2.)
        if not good:
            pending=[]
            continue
        if pending and (i!=pending[-1][0]+1 or s<pending[-1][1]-config.reverse_tolerance_m or
                        s-pending[-1][1]>max(5.,2*steps[i-1]+2.)):
            pending=[]
        pending.append((i,s));previous=s
        if len(pending)>=3 and s-pending[0][1]>=2*h:
            active=[];local_max=max(highwater,pending[0][1])
            for index,position in pending:
                local_max=max(local_max,position);progress[index]=local_max;active.append(index)
            highwater=local_max;runs.append(active);pending=[];last_trusted=i;travel=0.

    maps=[];valid=np.zeros(n,bool)
    for indexes in runs:
        ss=progress[indexes].copy();tt=t[indexes].copy()
        first,last=float(ss[0]+h),float(ss[-1]-h)
        if allow_boundaries and indexes[0]==0 and abs(ss[0])<=config.boundary_margin_m:
            ss=np.r_[0.,ss];tt=np.r_[0.,tt];first=0.
        if allow_boundaries and indexes[-1]==n-1 and abs(length-ss[-1])<=config.boundary_margin_m:
            ss=np.r_[ss,length];tt=np.r_[tt,lap.duration_s];last=length
        if last<=first or ss[-1]<=ss[0] or tt[-1]<=tt[0]:
            continue
        # A run is forward-only and cannot share interior progress with another.
        if maps and first<=maps[-1]['end_s_m']:
            continue
        mapping=TimeMap(ss-ss[0],tt-tt[0],ss[-1]-ss[0],tt[-1]-tt[0])
        run=dict(start_s_m=first,end_s_m=last,s0=float(ss[0]),t0=float(tt[0]),mapping=mapping)
        run['start_time_s']=float(run['t0']+mapping.at(first-run['s0']))
        run['end_time_s']=float(run['t0']+mapping.at(last-run['s0']))
        maps.append(run)
        local=np.asarray(indexes);valid[local]=(progress[local]>=first)&(progress[local]<=last)
    mapping=RegionalTimeMap(maps,length,lap.duration_s) if maps else None
    return mapping,np.where(valid,progress,np.nan),offsets,valid
