#!/usr/bin/python

import sys
import ocl
import camvtk
import time
import vtk
import math
import area
import ngc_writer as nw

import config_pb2
from google.protobuf import text_format

config = None

def ReadConfig(fn):
    basename = fn
    if fn.endswith(".conf"):
        basename = fn[:len(fn)-len(".conf")]

    with open(fn, "r") as f:
        content = f.read()
    global config
    config = config_pb2.Config()

    config.in_filename = basename + ".stl"
    config.out_filename = basename + ".ngc"
    text_format.Merge(content, config)

class TriangleProcessor(object):
    def __init__(self, tr):
        self.p = tr.getPoints()
        self.low = min(p.z for p in self.p)
        self.high = max(p.z for p in self.p)
        self.n = tr.n

    def Horizontal(self):
        if self.n.z < 0:
            return False
        return self.high - self.low >= 0 and self.high - self.low < 0.05

    def Vertical(self):
        d = self.n.dot(ocl.Point(0,0,1))
        return abs(d) < 0.01

    def Level(self):
        return self.low

def seq(pl):
    ret = []
    for p in pl:
        ret.append([p.x, p.y, p.z])
    return ret

def drawLoops(myscreen, loops):
    points = []
    for loop in loops:
        for p in loop:
            points.append(p)
    myscreen.addActor(camvtk.PointCloud(points))

def IsNegative(prev, vertex):
    p1 = prev - vertex.c
    p2 = vertex.p - vertex.c

    smaller_angle_ccw = (p1 ^ p2 > 0)
    if vertex.type == 1:  # CCW arc, positive iff smaller angle is CCW
        return smaller_angle_ccw
    else:  # CW arc, positive if smaller angle is CW
        return not smaller_angle_ccw

def drawCurve(myscreen, curve, z):
    vertices = curve.getVertices()
    current = vertices[0].p
    #print "start at (%.2f, %.2f) z=%.2f" % (current.x, current.y, z)
    for v in vertices[1:]:
        if v.type == 0:
            #print "line to (%.2f,%.2f) z=%.2f" % (v.p.x, v.p.y, z)
            myscreen.addActor(camvtk.Line(p1=(current.x, current.y, z), p2 = (v.p.x, v.p.y, z)))
        else:
            r = math.hypot(v.p.x-v.c.x, v.p.y-v.c.y)
            #print "arc to (%.2f,%.2f) center=(%.2f,%.2f) r=%.2f z=%.2f" % (v.p.x, v.p.y, v.c.x, v.c.y, r, z)
            src = vtk.vtkArcSource()
            src.SetCenter(v.c.x, v.c.y, z)
            src.SetPoint1(current.x, current.y, z)
            src.SetPoint2(v.p.x, v.p.y, z)
            src.SetResolution(20)
            src.SetNegative(not IsNegative(current, v))
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInput(src.GetOutput())
            actor = camvtk.CamvtkActor()
            actor.SetMapper(mapper)
            myscreen.addActor(actor)
        current = v.p

def GetEssentialLevels(s):
    levels = []
    good = 0
    total = 0
    for t in s.getTriangles():
        tr = TriangleProcessor(t)
        total += 1
        if tr.Horizontal():
            levels.append(tr.Level())
            good += 1
        elif tr.Vertical():
            good += 1
        else:
            p = seq(t.getPoints())
    print "good=", good, " total=", total

    levels.sort()
    print levels
    essential_levels = []
    i = 0
    while i < len(levels):
        l0 = levels[i]
        j = i+1
        while j < len(levels):
            l1 = levels[j]
            if l1 > l0 + 0.1:
                break
            j += 1
        essential_levels.append(l0)
        i = j
    essential_levels.sort(reverse=True)
    essential_levels = [l for l in essential_levels if l >= config.bottom]
    if len(essential_levels) == 0 or essential_levels[len(essential_levels) - 1] != config.bottom:
        essential_levels.append(config.bottom)

    return essential_levels

def GetWaterlines(s, essential_levels):
    cutter = ocl.CylCutter(config.tool_diameter, 20)
    level_loops = []
    for l in essential_levels:
        print "level=", l
        wl = ocl.Waterline()
        wl.setSTL(s)
        wl.setCutter(cutter)
        wl.setSampling(0.02)
        wl.setZ(l)
        wl.run2()
        level_loops.append(wl.getLoops())

    return level_loops

def MakeArea(loops):
    ar = area.Area()
    for loop in loops:
        curve = area.Curve()
        for p in loop:
            curve.append(area.Point(p.x, p.y))
        ar.append(curve)
    ar.FitArcs()
    ar.Reorder()
    return ar

def ConvertLoopsToAreas(level_loops):
    ret = []
    for i, loops in enumerate(level_loops):
        print "Processing", i, "th level:"
        ar = MakeArea(loops)
        print "Area made"
        ret.append(ar)
    print "Done processing"
    return ret

def MakeCutAreas(levels, areas):
    outer_bound = area.Area(areas[len(areas) - 1])
    outer_bound.Offset(-3.175)
    cut_levels = [ config.top ]
    cut_areas = [ outer_bound ]
    for i, ar in enumerate(areas):
        for curve in outer_bound.getCurves():
            ar.append(curve)
        ar.Reorder()
        cut_areas.append(ar)
        cut_levels.append(levels[i])
    return cut_levels, cut_areas

def MakeLevelToolpaths(levels, areas):
    tps = []
    for i, ar in enumerate(areas):
        print "Making", i, "th toolpath at", levels[i]
        tp = ar.MakePocketToolpath(3.175, -3.175, config.step_over, True, False, 0)
        tps.append(tp)
        print " -- Got", len(tp), "curves"
    print "Out:", len(tps), "levels"
    return levels, tps

def MakeCompleteToolpath(tp_levels, tp_paths):
    cur_lev = tp_levels[0]
    cur_tp = tp_paths[0]
    next_levels_idx = 1

    levs = [ ]
    tps = [ ]
    while cur_lev > config.bottom - config.vertical_tolerance:
        levs.append(cur_lev)
        tps.append(cur_tp)

        cur_lev -= config.step_down

        if (next_levels_idx < len(tp_levels) and
            cur_lev < tp_levels[next_levels_idx] + config.vertical_tolerance):
            cur_tp = tp_paths[next_levels_idx]
            cur_lev = tp_levels[next_levels_idx]
            next_levels_idx += 1
    return levs, tps

class FileWriter(object):
    def __init__(self, fn):
        self.f = open(fn, "w")

    def Print(self, *x):
        s = [ str(t) for t in x ]
        self.f.write(" ".join(s))
        self.f.write('\n')

    def Close(self):
        self.f.close()

def OutputGCode(lev, paths, fn):
    nw.clearance_height = config.clearance_height
    nw.feed_height = config.feed_height
    nw.feed = config.feed
    nw.plunge_feed = config.plunge_feed

    nw.writer = FileWriter(fn)

    nw.comment("============ START G-CODE ===============")
    nw.preamble()
    nw.pen_up()
    pairs = zip(lev, paths)
    for lev, path in sorted(pairs, key = lambda(p): -p[0]):
        nw.comment("level=%s" % lev)
        for curve in path:
            vertices = curve.getVertices()
            current = vertices[0].p
            nw.xy_rapid_to(current.x, current.y)
            nw.pen_down(lev)
            for v in vertices[1:]:
                if v.type == 0:
                    nw.line_to(v.p.x, v.p.y, lev)
                else:
                    r = math.hypot(v.p.x - v.c.x, v.p.y - v.c.y)
                    nw.xy_arc_to(v.p.x, v.p.y, r, v.c.x, v.c.y, v.type != 1)
            nw.pen_up()
    nw.postamble()
    nw.comment("============ END G-CODE ===============")
    
    nw.writer.Close()

if __name__ == "__main__": 
    print ocl.version()
    if len(sys.argv) == 1:
        print "Usage: autocut [config filename]"
        sys.exit(1)

    ReadConfig(sys.argv[1])
    
    stl = camvtk.STLSurf(config.in_filename, color=camvtk.green)
    stl.SetOpacity(0.2)
    stl.RotateX(config.rotate_x)
    stl.RotateY(config.rotate_y)
    stl.RotateZ(config.rotate_z)
    print "STL surface read"
    polydata = stl.src.GetOutput()
    s= ocl.STLSurf()
    camvtk.vtkPolyData2OCLSTL(polydata, s)
    s.rotate(config.rotate_x * math.pi / 180,
             config.rotate_y * math.pi / 180,
             config.rotate_z * math.pi / 180)
    bb = s.getBounds()
    sx = max(abs(bb[0]), abs(bb[1]))
    sy = max(abs(bb[1]), abs(bb[2]))
    ms = max(sx, sy)
    print "STLSurf with ", s.size(), " triangles"

    essential_levels = GetEssentialLevels(s)
    level_loops = GetWaterlines(s, essential_levels)

    for i, lev in enumerate(essential_levels):
        lengths = [str(len(loop)) for loop in level_loops[i]]
        print "L%02d@%smm: %s" % (i, lev, ",".join(lengths))

    # cut_levels, cut_loops = PopulateIntermediateLevels(essential_levels, level_loops)
    # print "------------------------"
    # print "cut levels: %d, cut_loops: %d" % (len(cut_levels), len(cut_loops))
    # for i, lev in enumerate(cut_levels):
    #     lengths = [str(len(loop)) for loop in cut_loops[i]]
    #     if i > 0:
    #         print "L%02d@%smm: %s (d=%s)" % (i, lev, len(lengths), cut_levels[i-1]-lev)
    #     else:
    #         print "L%02d@%smm: %s" % (i, lev, len(lengths))

    # print "------------------------"

    #    pocket_tps = [ MakePocket(loops, config.step_over) for loops in cut_loops ]
    #    pocket_tps = [ MakePocket(loops, config.step_over) for loops in level_loops]

    level_areas = ConvertLoopsToAreas(level_loops)
    cut_levels, cut_areas = MakeCutAreas(essential_levels, level_areas)
    tp_levels, tp_paths = MakeLevelToolpaths(cut_levels, cut_areas)
    tp_levels, tp_paths = MakeCompleteToolpath(tp_levels, tp_paths)

    OutputGCode(tp_levels, tp_paths, config.out_filename)

    myscreen = camvtk.VTKScreen()    
    myscreen.addActor(stl)

    for i, lev in enumerate(tp_levels):
       tp = tp_paths[i]
       print "Lev", i, "@", lev, ":", len(tp), "curves"
       for c in tp:
           drawCurve(myscreen, c, lev)
    # all_loops = []
    # for loops in level_loops:
    #     all_loops += loops
    # drawLoops(myscreen, all_loops)
    
    myscreen.camera.SetPosition(3, 23, 15)
    myscreen.camera.SetFocalPoint(5, 5, 0)
    myscreen.render()
    print " All done."
    myscreen.iren.Start()
