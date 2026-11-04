.SILENT:

all: main

lib:
	make -C ../measure/

main: lib main.cpp
	g++ main.cpp -mavx -mavx2 -L../measure -I../measure -l:libmeasure.a -o main

run: main
	sudo taskset -c 1 ./main 4

clean:
	make -C ../measure/ clean
	rm -r main
