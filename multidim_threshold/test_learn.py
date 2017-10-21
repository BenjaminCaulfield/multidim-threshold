from itertools import product, combinations
from collections import namedtuple

import unittest
import hypothesis.strategies as st
from hypothesis import given, note, event
from lenses import lens
import pytest

import multidim_threshold as mdt
import numpy as np
import funcy as fn

from functools import partial

def to_rec(xs):
    bots = [b for b, _ in xs]
    tops = [max(b + d, 1) for b, d in xs]
    intervals = tuple(zip(bots, tops))
    return mdt.Rec(intervals=intervals)

GEN_RECS = st.builds(to_rec, st.lists(st.tuples(
    st.floats(min_value=0, max_value=1), 
    st.floats(min_value=0, max_value=1)), min_size=1, max_size=5))


@given(GEN_RECS)
def test_vol(rec):
    assert 1 >= mdt.volume(rec) >= 0


def relative_lo_hi(r, i1, i2):
    lo, hi = sorted([i1, i2])
    bot, diag = np.array(r.bot), np.array(r.top) - np.array(r.bot)
    f = lambda t: bot + diag*t
    return tuple(f(lo)), tuple(f(hi))


@given(GEN_RECS)
def test_forward_cone(r):
    p = tuple((np.array(r.bot) + 0.1).clip(max=1))
    f = mdt.forward_cone(p, r)
    assert mdt.volume(r) >= mdt.volume(f) >= 0
    assert r.top == f.top
    assert all(x <= y for x, y in zip(r.bot, f.bot))


@given(GEN_RECS)
def test_backward_cone(r):
    p = (np.array(r.bot) + 0.1).clip(max=1)
    b = mdt.backward_cone(p, r)
    assert mdt.volume(r) >= mdt.volume(b) >= 0
    assert r.bot == b.bot
    assert all(x >= y for x, y in zip(r.top, b.top))


@given(GEN_RECS, st.floats(min_value=0, max_value=1), 
       st.floats(min_value=0, max_value=1))
def test_backward_forward_cone_relations(r, i1, i2):
    lo, hi = relative_lo_hi(r, i1, i2)
    b, f = mdt.backward_cone(hi, r), mdt.forward_cone(lo, r)
    # TOOD
    #assert mdt.utils.intersect(b, f)
    intervals = tuple(zip(b.bot, f.top))
    assert r == mdt.Rec(intervals=intervals)


@given(GEN_RECS, st.floats(min_value=0, max_value=1), 
       st.floats(min_value=0, max_value=1))
def test_gen_incomparables(r, i1, i2):
    lo, hi = relative_lo_hi(r, i1, i2)
    n = len(r.bot)
    subdivison = list(mdt.subdivide(lo, hi, r))
    # TODO
    #if n == 1 or mdt.Rec(tuple(zip(lo, hi))) == r:
    #    assert len(subdivison) == 0
    #    return
    #assert len(subdivison) != 0

    v = mdt.volume(r)
    diam = np.linalg.norm(np.array(r.top) - np.array(r.bot))
    diam2 = np.linalg.norm(np.array(hi) - np.array(lo))
    # TODO
    #if v == 0:
    #    assert max(mdt.volume(r2) for r2 in subdivison) == 0
    #elif diam != pytest.approx(diam2):
    #    assert max(mdt.volume(r2) for r2 in subdivison) < v

    # test Containment
    #assert all(mdt.utils.contains(r, i) for i in subdivison)

    # test Intersections
    subdivison = set(subdivison)
    # TODO
    #assert all(mdt.utils.intersect(i, i2) for i, i2 in
    #           combinations(subdivison, 2))


@given(GEN_RECS)
def test_box_edges(r):
    n = len(r.bot)
    m = len(list(mdt.box_edges(r)))
    assert m == n*2**(n-1)


def _staircase(n):
    xs = np.linspace(0, 0.9, n)
    xs = list(fn.mapcat(lambda x: [x, x], xs))[1:]
    ys = xs[::-1]
    return xs, ys


def staircase_oracle(xs, ys):
    return lambda p: any(p[0] >= x and p[1] >= y for x,y in zip(xs, ys))


GEN_STAIRCASES = st.builds(_staircase, st.integers(min_value=2, max_value=6))
GEN_POINTS = st.lists(st.tuples(st.floats(min_value=0, max_value=1), 
                                st.floats(min_value=0, max_value=1)), max_size=100)

@given(GEN_STAIRCASES, GEN_POINTS)
def test_staircase_oracle(xys, test_points):
    xs, ys = xys
    f = staircase_oracle(xs, ys)
    # Check that staircase works as expected

    for x, y in zip(xs, ys):
        assert f((x, y))
        assert f((x + 0.1, y+0.1))
        assert not f((x-0.1, y-0.1))

    for a, b in test_points:
        assert f((a, b)) == any(a >= x and b >= y for x, y in zip(*xys))

    


@given(GEN_STAIRCASES)
def test_staircase_refinement(xys):
    xs, ys = xys
    f = staircase_oracle(xs, ys)

    # Check bounding box is tight
    max_xy = np.array([max(xs), max(ys)])
    unit_rec = mdt.Rec(((0, 1), (0,1)))
    bounding = mdt.bounding_box(unit_rec, f)

    assert all(a >= b for a,b in zip(unit_rec.top, bounding.top))
    assert all(a <= b for a,b in zip(unit_rec.bot, bounding.bot))
    np.testing.assert_array_almost_equal(bounding.top, max_xy, decimal=1)

    
    refiner = mdt.volume_guided_refinement([unit_rec], oracle=f)
    prev = None
    # Test properties until refined to fixed point
    for i, tagged_rec_set in enumerate(refiner):
        rec_set = set(r for _, r in tagged_rec_set)
        # TODO: assert convergence rather than hard coded limit
        if max(mdt.volume(r) for r in rec_set) < 1e-3:
            break
        assert i <= 2*len(xs)
        prev = rec_set

    # TODO: check that the recset contains the staircase
    # Check that the recset refines the previous one
    event(f"len {len(rec_set)}")
    event(f"volume {max(mdt.volume(r) for r in rec_set)}")
    if len(rec_set) > 1:
        assert all(any(mdt.utils.contains(r1, r2) for r2 in rec_set) 
                   for r1 in prev)

        # Check that the recset is not disjoint
        # TODO
        # assert all(any(mdt.utils.intersect(r1, r2) for r2 in rec_set - {r1}) 
        # for r1 in rec_set)

    # Check that for staircase shape
    # TODO: rounding to the 1/len(x) should recover xs and ys

EPS=1e-1

@given(GEN_RECS)
def test_rec_bounds(r):
    lb = mdt.utils.dist_rec_lowerbound(r,r)
    ub = mdt.utils.dist_rec_upperbound(r,r)
    assert 0 == lb
    if mdt.utils.degenerate(r):
        assert 0 == ub

    bot, top = np.array(r.bot), np.array(r.top)
    diam = np.linalg.norm(top - bot, ord=float('inf'))
    r2 = mdt.Rec(tuple(zip(bot + (diam + 1), top + (diam + 1))))
    ub = mdt.utils.dist_rec_upperbound(r,r2)
    lb = mdt.utils.dist_rec_lowerbound(r,r2)

    assert lb <= ub
    assert diam <= ub


Point2d = namedtuple("Point2d", ['x', 'y'])
class Interval(namedtuple("Interval", ['start', 'end'])):
    def __contains__(self, point):
        return (self.start.x <= point.x <= self.end.x 
                and self.start.y <= point.y <= self.end.y)


def hausdorff(x, y):
    f = lambda a, b: np.linalg.norm(a - b, ord=float('inf'))
    return max(mdt.directed_hausdorff(x, y, metric=f),
               mdt.directed_hausdorff(y, x, metric=f))


def staircase_hausdorff(f1, f2, return_expanded=False):
    def additional_points(i1, i2):
        '''Minimal distance points between intvl1 and intvl2.''' 
        xs1, xs2 = {i1.start.x, i1.end.x}, {i2.start.x, i2.end.x}
        ys1, ys2 = {i1.start.y, i1.end.y}, {i2.start.y, i2.end.y}
        all_points = [Point2d(x, y) for x, y in 
                      fn.chain(product(xs1, ys2), product(xs2, ys1))]
        new_f1 = {p for p in all_points if p in i1}
        new_f2 = {p for p in all_points if p in i2}
        return new_f1, new_f2

    f1_intervals = [Interval(p1, p2) for p1, p2 in zip(f1, f1[1:])]
    f2_intervals = [Interval(p1, p2) for p1, p2 in zip(f2, f2[1:])]    
    f1_extras, f2_extras = zip(*(additional_points(i1, i2) for i1, i2 in
                                 product(f1_intervals, f2_intervals)))
    F1 = np.array(list(set(f1) | set.union(*f1_extras)))
    F2 = np.array(list(set(f2) | set.union(*f2_extras)))
    return hausdorff(F1, F2)


@given(st.integers(min_value=0, max_value=10), GEN_STAIRCASES, GEN_STAIRCASES)
def test_staircase_hausdorff(k, xys1, xys2):
    def discretize(intvl):
        p1, p2 = intvl
        xs = np.linspace(p1.x, p2.x, 2+k) 
        ys = np.linspace(p1.y, p2.y, 2+k)
        return [Point2d(x, y) for x, y in product(xs, ys)]

    f1 = [Point2d(x, y) for x,y in zip(*xys1)]
    f2 = [Point2d(x, y) for x,y in zip(*xys2)]

    f1_hat = set(fn.mapcat(discretize, zip(f1, f1[1:])))
    f2_hat = set(fn.mapcat(discretize, zip(f2, f2[1:])))

    # Check discretization works as expected
    assert len(f1_hat) == (len(f1)-1)*k + len(f1)
    assert len(f2_hat) == (len(f2)-1)*k + len(f2)

    # Check extended array has smaller distance
    d1 = hausdorff(np.array(f1), np.array(f2))
    d2 = staircase_hausdorff(f1, f2)
    assert d2 <= d1


@given(st.tuples(GEN_STAIRCASES, GEN_STAIRCASES))
def test_staircase_hausdorff_bounds(data):
    (xs1, ys1), (xs2, ys2) = data

    f1 = [Point2d(x, y) for x,y in zip(*(xs1, ys1))]
    f2 = [Point2d(x, y) for x,y in zip(*(xs2, ys2))]

    o1 = staircase_oracle(xs1, ys1)
    o2 = staircase_oracle(xs2, ys2)
    unit_rec = mdt.Rec(((0, 1), (0, 1)))
    bounding1 = mdt.bounding_box(unit_rec, o1)
    bounding2 = mdt.bounding_box(unit_rec, o2)
    
    refiner1 = mdt.volume_guided_refinement([unit_rec], o1)
    refiner2 = mdt.volume_guided_refinement([unit_rec], o2)

    d12 = staircase_hausdorff(f1, f2)
    
    for queue1, queue2 in zip(refiner1, refiner2):
        rec_set1 = set(r for _, r in queue1)
        rec_set2 = set(r for _, r in queue2)
        d12_lb, d12_ub = mdt.approx_dH_inf(rec_set1, rec_set2)
        assert d12_lb <= d12
        assert d12 <= d12_ub
        note(f"{d12_ub - d12_lb}")
        if max(queue1[0][0], queue2[0][0]) < 1e-2:
            break
