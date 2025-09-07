CXX = g++
CXXFLAGS = -std=c++17 -O2 -Wall

TARGET = simulated_annealing
OBJS = simulated_annealing.o score.o globals.o

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CXX) $(CXXFLAGS) -o $@ $^

simulated_annealing.o: simulated_annealing.cpp score.h globals.h
	$(CXX) $(CXXFLAGS) -c simulated_annealing.cpp

score.o: score.cpp score.h globals.h
	$(CXX) $(CXXFLAGS) -c score.cpp

globals.o: globals.cpp globals.h
	$(CXX) $(CXXFLAGS) -c globals.cpp

clean:
	rm -f $(OBJS) $(TARGET)

.PHONY: all clean
