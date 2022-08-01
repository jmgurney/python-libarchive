CFLAGS     = -g 
INCLUDE    = -I/usr/local/include -I/usr/include -I.
LIBS       = -L /usr/local/lib -larchive

#DEFINES = -DPyUnicode_AS_STRING=PyUnicode_AS_DATA
PYVER ?= 3.9

all: __libarchive.so

_libarchive_wrap.c: _libarchive.i
	#swig -python -c++ -Wall -shadow _libarchive.i
	swig -python -Wall -shadow  _libarchive.i

_libarchive_wrap.o: _libarchive_wrap.c
	echo ${CC} -c ${CFLAGS} -fPIC  $$(python${PYVER}-config --cflags) _libarchive_wrap.c
	${CC} -c ${CFLAGS} -fPIC  $$(python${PYVER}-config --cflags) ${DEFINES} _libarchive_wrap.c
#	${CXX} -c ${CFLAGS} -fPIC  $$(python${PYVER}-config --cflags) -DPyUnicode_AS_STRING=PyUnicode_AS_DATA _libarchive_wrap.cxx

__libarchive.so: _libarchive_wrap.o
	echo INCLUDE=$INCLUDE LIBS=$LIBS
	${CC} _libarchive_wrap.o -shared $$(python${PYVER}-config --ldflags) -Wl,-soname=__libarchive.so -o __libarchive.so ${LIBS}

clean:
	rm -f *.o *.so *.pyc