import os
import re

class ExplorationLogParser:
    def __init__(self, log_directory, console_prefix):
        self.log_dir = log_directory
        self.prefix = console_prefix

    def list_log_files(self):
        if not os.path.exists(self.log_dir):
            return []
        files = [f for f in os.listdir(self.log_dir) if f.startswith(self.prefix) and f.endswith(".txt")]
        files.sort(reverse=True)
        return files

    def parse_summary_from_file(self, log_filepath):
        try:
            with open(log_filepath, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"[ERRORE] Impossibile leggere il file {log_filepath}: {e}")
            return []

        summary_started = False
        summary_lines = []
        
        for line in lines:
            if "RIEPILOGO GENERALE DELLA MISSIONE" in line or "RIEPILOGO" in line:
                summary_started = True
                continue
            if summary_started:
                if "MISSIONE CONCLUSA" in line:
                    break
                summary_lines.append(line)
                
        return summary_lines

    def extract_planets_data(self, summary_lines):
        parsed_planets = {}
        current_section = None
        
        planet_pattern = re.compile(
            r"^[•\-*]\s*(?P<planet_name>[\w\s'.:/-]+?)\s*\(Sistema:\s*(?P<star_name>[\w\s'-]+)\)(?:\s*-\s*(?P<life_info>.+))?"
        )
        lc_pattern = re.compile(r"LC:\s*([\d\.]+)")
        disp_pattern = re.compile(r"Profilo:\s*([\w\s'-]+)")

        for line in summary_lines:
            line_str = line.strip()
            if not line_str:
                continue
            line_lower = line_str.lower()
            
            if "abitabili" in line_lower:
                current_section = "habitable"
                continue
            elif "colonie" in line_lower:
                current_section = "colonies"
                continue
            elif "tracce di vita" in line_lower:
                current_section = "life"
                continue
            elif "civilta" in line_lower:
                current_section = "civilizations"
                continue

            if current_section and (line_str.startswith("-") or line_str.startswith("•")):
                match = planet_pattern.match(line_str)
                if match:
                    data = match.groupdict()
                    p_name = data['planet_name'].strip()
                    s_name = data['star_name'].strip()
                    
                    key = (p_name, s_name)
                    if key not in parsed_planets:
                        parsed_planets[key] = {
                            "planet_name": p_name, "star_name": s_name,
                            "is_habitable_candidate": False, "is_colonized": False,
                            "has_life": False, "is_intelligent": False,
                            "lc": None, "disposition": None, "life_desc": None
                        }
                    entry = parsed_planets[key]
                    
                    if current_section == "habitable":
                        entry["is_habitable_candidate"] = True
                    elif current_section == "colonies":
                        entry["is_colonized"] = True
                        
                    if data['life_info'] and current_section in ("life", "civilizations"):
                        entry["has_life"] = True
                        info_str = data['life_info'].strip()
                        entry["life_desc"] = info_str
                        
                        lc_m = lc_pattern.search(info_str)
                        if lc_m:
                            entry["lc"] = float(lc_m.group(1))
                            
                        disp_m = disp_pattern.search(info_str)
                        if disp_m:
                            entry["disposition"] = disp_m.group(1).strip()
                            
                        if "Civiltà" in info_str:
                            entry["is_intelligent"] = True
                            
        return list(parsed_planets.values())