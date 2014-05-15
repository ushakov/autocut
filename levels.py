import ocl
import camvtk
import time
import vtk
import math

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

def drawLoops(myscreen, loops, color):
    points = []
    for loop in loops:
        for p in loop:
            points.append(p)
    myscreen.addActor(camvtk.PointCloud(points))
            
kTop = 14
kBottom = 0


if __name__ == "__main__":  
    print ocl.version()
    
    stl = camvtk.STLSurf("wheel-rim.stl", color=camvtk.green)
    stl.RotateY(-90)
    print "STL surface read"
    polydata = stl.src.GetOutput()
    s= ocl.STLSurf()
    camvtk.vtkPolyData2OCLSTL(polydata, s)
    s.rotate(0,-math.pi/2,0)
    bb = s.getBounds()
    sx = max(abs(bb[0]), abs(bb[1]))
    sy = max(abs(bb[1]), abs(bb[2]))
    ms = max(sx, sy)
    print "STLSurf with ", s.size(), " triangles"

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
    essential_levels = [l for l in essential_levels if l >= kBottom]
    if len(essential_levels) == 0 or essential_levels[len(essential_levels) - 1] != kBottom:
        essential_levels.append(kBottom)

    cutter = ocl.CylCutter(3.175, 20)
    all_loops = []
    for l in essential_levels:
        print "level=", l
        wl = ocl.Waterline()
        wl.setSTL(s)
        wl.setCutter(cutter)
        wl.setSampling(0.02)
        wl.setZ(l + 0.001)
        wl.run2()
        for lp in wl.getLoops():
            all_loops.append(lp)

    print "levels:", [ "%s" % l for l in essential_levels ]
    
    myscreen = camvtk.VTKScreen()    
    myscreen.addActor(stl)

    drawLoops(myscreen, all_loops, camvtk.red)
    
    myscreen.camera.SetPosition(3, 23, 15)
    myscreen.camera.SetFocalPoint(5, 5, 0)
    myscreen.render()
    print " All done."
    myscreen.iren.Start()
