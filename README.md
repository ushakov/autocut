Autocut -- automatic toolpath generator for 2.5D solids
=======================================================

Note! This is prototype, don't expect it to work at all.

Requirements:
-------------

* opencamlib (patched)
* libarea (compiled with clipper)
* google protobug library (including python libs)

Comments
--------

### Opencamlib needs to be patched.

The following patch should be applied:

    --- a/src/ocl_geometry.cpp
    +++ b/src/ocl_geometry.cpp
    @@ -115,6 +115,7 @@ void export_geometry() {
             .def("getPoints", &Triangle_py::getPoints)
             .def("__str__", &Triangle_py::str) 
             .def_readonly("p", &Triangle_py::p)
    +        .def_readonly("n", &Triangle_py::n)
         ;
         bp::class_<STLSurf>("STLSurf_base") // needed by STLSurf_py below
         ;

### libarea should be compiled with clipper

To do that, compile like this:

    make -f Makefileclipper

### Licensing

Opencamlib is GPLv3, libarea is BSD, so this work is GPLv3 also.
