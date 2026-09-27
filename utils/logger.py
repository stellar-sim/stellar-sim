################################################################################
# FILE: utils/logger.py
################################################################################

import sys

class Tee:
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            try: f.write(obj)
            except Exception: pass
    def flush(self):
        for f in self.files:
            try: f.flush()
            except Exception: pass

class ASCIIExplorationLogger:
    VERBOSITY_SILENT = 0
    VERBOSITY_COMPACT = 1
    VERBOSITY_FULL = 2

    def __init__(self, verbosity=1):
        self.simulation_time_hours = 0
        self.verbosity = verbosity

    def get_time_str(self):
        years = self.simulation_time_hours / (24 * 365.25)
        return f"T + {years:6.2f} yr"

    def log_header(self, title):
        if self.verbosity == 0: return
        sys.stdout.write("\n" + "=" * 80 + "\n" + f"=== {title.upper()} ===\n" + "=" * 80 + "\n")
        sys.stdout.flush()

    def log_travel(self, from_name, to_name, target_id, dist_ly):
        if self.verbosity < self.VERBOSITY_FULL: return
        sys.stdout.write(f"[{self.get_time_str()}] [TRAIETTORIA] {from_name} -> {to_name} ({dist_ly:.2f} ly)\n")
        sys.stdout.flush()

    def log_event(self, category, details, duration_hours=0, indent=2, min_verbosity=1):
        self.simulation_time_hours += duration_hours
        if self.verbosity == 0 or self.verbosity < min_verbosity: return
        sys.stdout.write(" " * indent + f"[{self.get_time_str()}] [{category.upper()}] {details}\n")
        sys.stdout.flush()

    def log_raw(self, line, indent=0, min_verbosity=1):
        if self.verbosity == 0 or self.verbosity < min_verbosity: return
        sys.stdout.write(" " * indent + line + "\n")
        sys.stdout.flush()

    def close_log(self):
        if self.verbosity == 0: return
        years = self.simulation_time_hours / (24 * 365.25)
        sys.stdout.write("\n" + "=" * 80 + "\n" + f"MISSIONE CONCLUSA | Tempo operativo totale: {years:.2f} anni stellari.\n" + "=" * 80 + "\n")
        sys.stdout.flush()