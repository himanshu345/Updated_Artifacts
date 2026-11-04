# Makefile – auto-build every bench_*.c and then launch the sweep
CC      := gcc
CFLAGS  := -O2 -march=native -std=gnu11 -Wall -Wextra

SRC_DIR := src
BIN_DIR := bin

# Pick up any new bench_*.c you drop into src/
BENCH_SRC := $(wildcard $(SRC_DIR)/bench_*.c)
BENCH_BIN := $(patsubst $(SRC_DIR)/%.c,$(BIN_DIR)/%,$(BENCH_SRC))

.PHONY: all compile measure clean

# ---- default target ---------------------------------------------------------
all: compile measure

compile: $(BIN_DIR) $(BENCH_BIN)
# ---- compile rule -----------------------------------------------------------
$(BIN_DIR)/bench_%: $(SRC_DIR)/bench_%.c
	$(CC) $(CFLAGS) -o $@ $<

# ---- create bin/ if missing -------------------------------------------------
$(BIN_DIR):
	mkdir -p $(BIN_DIR)

# ---- post-build sweep -------------------------------------------------------
measure:
	@echo "removing old measurement data"
	rm -f data/loop_energy.csv
	@echo "—— Build finished, launching measurement sweep ——"
	@start=$$(date +%s); \
	sudo ./scripts/sweep_all.sh; \
	end=$$(date +%s); \
	echo "—— Sweep completed in $$((end - start)) seconds ——"

# ---- clean helper -----------------------------------------------------------
clean:
	rm -f $(BIN_DIR)/bench_*
	rm -f data/loop_energy.csv
