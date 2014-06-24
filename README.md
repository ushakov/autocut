Autocut -- automatic toolpath generator for 2.5D solids
=======================================================

Note! This is prototype, don't expect it to work at all.

Requirements:
-------------

* python-vtk libboost-python-dev python-protobuf
* opencamlib (patched)
* libarea (compiled with clipper)

Comments
--------

### Opencamlib needs to be patched.

Checkout [Opencamlib](https://github.com/aewallin/opencamlib) source code with:

    git clone https://github.com/aewallin/opencamlib

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

Checkout [libarea](https://github.com/Heeks/libarea) code with:

    git clone https://github.com/Heeks/libarea

To do that, compile like this:

    make -f Makefileclipper
    make -f Makefileclipper install

### Licensing

Opencamlib is GPLv3, libarea is BSD, so this work is GPLv3 also.
