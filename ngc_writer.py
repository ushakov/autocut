# Based on "very simple G-code writer" by Anders Wallin 2012

clearance_height= 20
feed_height = 10
feed = 200
plunge_feed = 100
metric = True

class Writer(object):
    def Print(self, *x):
        s = [ str(t) for t in x ]
        print " ".join(s)

writer = Writer()

def line_to(x,y,z):
    writer.Print("G1 X% 8.6f Y% 8.6f Z% 8.6f F%.0f" % (x, y, z, feed))

def xy_line_to(x,y):
    writer.Print("G1 X% 8.4f Y% 8.4f " % (x, y))

# (endpoint, radius, center, cw?)
def xy_arc_to( x,y, r, cx,cy, cw ):
    if (cw):
        writer.Print("G2 X% 8.5f Y% 8.5f R% 8.5f" % (x, y, r))
    else:
        writer.Print("G3 X% 8.5f Y% 8.5f R% 8.5f" % (x, y, r))
    # FIXME: optional IJK format arcs
    
def xy_rapid_to(x,y):
    writer.Print("G0 X% 8.4f Y% 8.4f " % (x, y))

def pen_up():
    writer.Print("G0Z% 8.4f " % (clearance_height))

"""
def pen_down():
    writer.Print("G0Z% 8.4f" % (feed_height))
    plunge(0)
"""

def pen_down(z=0):
    writer.Print("G0Z% 8.4f" % (feed_height))
    plunge(z)

def plunge(z):
    writer.Print("G1 Z% 8.4f F% 8.0f" % (z, plunge_feed))

def preamble():
    if (metric):
        writer.Print("G21 F% 8.0f" % (feed)) # G20 F6 for inch
    else:
        writer.Print("G20 F% 8.0f" % (feed)) # G20 F6 for inch
        
    writer.Print("G64 P0.001") # linuxcnc blend mode
    pen_up()
    writer.Print("G0 X0 Y0") # this might not be a good idea!?

def postamble():
    pen_up()
    writer.Print("M2") # end of program

def comment(s=""):
    writer.Print("( ",s," )")
    
if __name__ == "__main__":
    print "Nothing to see here."
