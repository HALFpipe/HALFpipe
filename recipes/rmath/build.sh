#!/bin/bash

export LIBnn=lib

./configure \
    --prefix="${PREFIX}" \
    --enable-lto=yes \
    --enable-R-profiling=no \
    --enable-byte-compiled-packages=no \
    --enable-java=no \
    --enable-nls=no \
    --enable-openmp=no \
    --enable-rpath=no \
    --with-aqua=no \
    --with-cairo=no \
    --with-ICU=no \
    --with-internal-tzcode=yes \
    --with-jpeglib=no \
    --without-libintl-prefix \
    --with-libpng=no \
    --with-libtiff=no \
    --with-readline=no \
    --with-recommended-packages=no \
    --with-tcltk=no \
    --with-x=no

pushd src/nmath/standalone || exit

make --jobs="$(nproc)" shared
make install

find "${PREFIX}"

popd || exit
