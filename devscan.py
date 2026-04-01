#!/usr/bin/env python3
"""
DevScan - Codebase Analyzer CLI
================================
Author: Julio Nunez Garcia

A command-line tool that scans project directories and generates
detailed reports on code structure, complexity, dependencies,
and quality metrics. Built for developers who want fast insight
into any codebase.

Usage:
    devscan /path/to/project
    devscan . --format json
    devscan ./src --ignore node_modules,dist --top 20
"""

import argparse
import os
import sys
import json
import re
import math
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime

__version__ = "1.2.0"

# ── Language definitions ──────────────────────────────────────
LANGUAGES = {
    ".py": {"name": "Python", "color": "\033[93m", "comment": "#", "multi": ('"""', '"""')},
    ".js": {"name": "JavaScript", "color": "\033[33m", "comment": "//", "multi": ("/*", "*/")},
    ".jsx": {"name": "React JSX", "color": "\033[36m", "comment": "//", "multi": ("/*", "*/")},
    ".ts": {"name": "TypeScript", "color": "\033[34m", "comment": "//", "multi": ("/*", "*/")},
    ".tsx": {"name": "React TSX", "color": "\033[36m", "comment": "//", "multi": ("/*", "*/")},
    ".java": {"name": "Java", "color": "\033[31m", "comment": "//", "multi": ("/*", "*/")},
    ".c": {"name": "C", "color": "\033[90m", "comment": "//", "multi": ("/*", "*/")},
    ".cpp": {"name": "C++", "color": "\033[35m", "comment": "//", "multi": ("/*", "*/")},
    ".h": {"name": "C/C++ Header", "color": "\033[90m", "comment": "//", "multi": ("/*", "*/")},
    ".rs": {"name": "Rust", "color": "\033[91m", "comment": "//", "multi": ("/*", "*/")},
    ".go": {"name": "Go", "color": "\033[96m", "comment": "//", "multi": ("/*", "*/")},
    ".rb": {"name": "Ruby", "color": "\033[31m", "comment": "#", "multi": ("=begin", "=end")},
    ".php": {"name": "PHP", "color": "\033[35m", "comment": "//", "multi": ("/*", "*/")},
    ".swift": {"name": "Swift", "color": "\033[91m", "comment": "//", "multi": ("/*", "*/")},
    ".kt": {"name": "Kotlin", "color": "\033[35m", "comment": "//", "multi": ("/*", "*/")},
    ".r": {"name": "R", "color": "\033[34m", "comment": "#", "multi": None},
    ".html": {"name": "HTML", "color": "\033[33m", "comment": None, "multi": ("<!--", "-->")},
    ".css": {"name": "CSS", "color": "\033[36m", "comment": None, "multi": ("/*", "*/")},
    ".scss": {"name": "SCSS", "color": "\033[35m", "comment": "//", "multi": ("/*", "*/")},
    ".sql": {"name": "SQL", "color": "\033[32m", "comment": "--", "multi": ("/*", "*/")},
    ".sh": {"name": "Shell", "color": "\033[32m", "comment": "#", "multi": None},
    ".yaml": {"name": "YAML", "color": "\033[33m", "comment": "#", "multi": None},
    ".yml": {"name": "YAML", "color": "\033[33m", "comment": "#", "multi": None},
    ".json": {"name": "JSON", "color": "\033[33m", "comment": None, "multi": None},
    ".md": {"name": "Markdown", "color": "\033[37m", "comment": None, "multi": None},
    ".xml": {"name": "XML", "color": "\033[33m", "comment": None, "multi": ("<!--", "-->")},
}

DEFAULT_IGNORE = {
    "node_modules", ".git", "__pycache__", ".venv", "venv", "env",
    ".next", "dist", "build", ".cache", ".idea", ".vscode",
    "target", "vendor", ".tox", "egg-info", ".eggs",
}

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
WHITE = "\033[97m"
GRAY = "\033[90m"


# ── Analysis engine ───────────────────────────────────────────
class CodeAnalyzer:
    def __init__(self, root_path, ignore_dirs=None, top_n=15):
        self.root = Path(root_path).resolve()
        self.ignore = ignore_dirs or DEFAULT_IGNORE
        self.top_n = top_n
        self.files = []
        self.stats = defaultdict(lambda: {
            "files": 0, "code": 0, "comment": 0,
            "blank": 0, "total": 0, "sizes": [],
        })
        self.all_files_data = []
        self.total_size = 0
        self.dependency_files = []
        self.todos = []
        self.complexity_scores = []

    def scan(self):
        """Walk the directory tree and analyze every recognized file."""
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [
                d for d in dirnames
                if d not in self.ignore and not d.startswith(".")
            ]
            for fname in filenames:
                fpath = Path(dirpath) / fname
                ext = fpath.suffix.lower()

                if ext in LANGUAGES:
                    self._analyze_file(fpath, ext)

                if fname in (
                    "package.json", "requirements.txt", "Pipfile",
                    "Cargo.toml", "go.mod", "Gemfile", "pom.xml",
                    "build.gradle", "composer.json",
                ):
                    self.dependency_files.append(fpath)

        return self

    def _analyze_file(self, fpath, ext):
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
        except (PermissionError, OSError):
            return

        lines = content.splitlines()
        lang = LANGUAGES[ext]
        code_lines = 0
        comment_lines = 0
        blank_lines = 0
        in_multiline = False

        for line in lines:
            stripped = line.strip()

            if not stripped:
                blank_lines += 1
                continue

            if in_multiline:
                comment_lines += 1
                if lang["multi"] and lang["multi"][1] in stripped:
                    in_multiline = False
                continue

            if lang["multi"] and stripped.startswith(lang["multi"][0]):
                comment_lines += 1
                if lang["multi"][1] not in stripped[len(lang["multi"][0]):]:
                    in_multiline = True
                continue

            if lang["comment"] and stripped.startswith(lang["comment"]):
                comment_lines += 1
            else:
                code_lines += 1

            # Track TODOs and FIXMEs
            upper = stripped.upper()
            if "TODO" in upper or "FIXME" in upper or "HACK" in upper:
                rel = fpath.relative_to(self.root)
                line_num = lines.index(line) + 1
                self.todos.append((str(rel), line_num, stripped[:80]))

        total = len(lines)
        size = fpath.stat().st_size
        self.total_size += size
        rel_path = str(fpath.relative_to(self.root))

        # Complexity estimate (cyclomatic-like)
        complexity = self._estimate_complexity(content, ext)
        self.complexity_scores.append((rel_path, complexity, code_lines))

        s = self.stats[ext]
        s["files"] += 1
        s["code"] += code_lines
        s["comment"] += comment_lines
        s["blank"] += blank_lines
        s["total"] += total
        s["sizes"].append(size)

        self.all_files_data.append({
            "path": rel_path,
            "ext": ext,
            "code": code_lines,
            "comment": comment_lines,
            "blank": blank_lines,
            "total": total,
            "size": size,
            "complexity": complexity,
        })

    def _estimate_complexity(self, content, ext):
        """Rough cyclomatic complexity by counting branching keywords."""
        patterns = {
            ".py": r"\b(if|elif|for|while|except|with|and|or)\b",
            ".js": r"\b(if|else if|for|while|catch|switch|case|\&\&|\|\|)\b",
            ".jsx": r"\b(if|else if|for|while|catch|switch|case|\&\&|\|\|)\b",
            ".ts": r"\b(if|else if|for|while|catch|switch|case|\&\&|\|\|)\b",
            ".tsx": r"\b(if|else if|for|while|catch|switch|case|\&\&|\|\|)\b",
            ".java": r"\b(if|else if|for|while|catch|switch|case|\&\&|\|\|)\b",
            ".c": r"\b(if|else if|for|while|switch|case|\&\&|\|\|)\b",
            ".cpp": r"\b(if|else if|for|while|switch|case|catch|\&\&|\|\|)\b",
            ".rs": r"\b(if|else if|for|while|match|loop|\&\&|\|\|)\b",
            ".go": r"\b(if|else if|for|switch|case|select|\&\&|\|\|)\b",
        }
        pattern = patterns.get(ext)
        if not pattern:
            return 0
        return len(re.findall(pattern, content))

    def get_dependencies(self):
        """Parse dependency files and return package counts."""
        deps = {}
        for fpath in self.dependency_files:
            fname = fpath.name
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                if fname == "package.json":
                    data = json.loads(content)
                    d = data.get("dependencies", {})
                    dd = data.get("devDependencies", {})
                    deps["npm"] = {"prod": len(d), "dev": len(dd), "total": len(d) + len(dd)}
                elif fname == "requirements.txt":
                    pkgs = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("#")]
                    deps["pip"] = {"total": len(pkgs)}
                elif fname == "Cargo.toml":
                    dep_count = content.count("[dependencies]")
                    deps["cargo"] = {"total": dep_count}
                elif fname == "go.mod":
                    requires = re.findall(r"require\s+\(([^)]+)\)", content, re.DOTALL)
                    count = sum(len(r.strip().splitlines()) for r in requires)
                    deps["go"] = {"total": count}
            except (json.JSONDecodeError, Exception):
                continue
        return deps

    def to_dict(self):
        """Export full analysis as a dictionary."""
        total_code = sum(s["code"] for s in self.stats.values())
        total_comment = sum(s["comment"] for s in self.stats.values())
        total_blank = sum(s["blank"] for s in self.stats.values())
        total_lines = sum(s["total"] for s in self.stats.values())
        total_files = sum(s["files"] for s in self.stats.values())

        return {
            "project": self.root.name,
            "path": str(self.root),
            "scanned_at": datetime.now().isoformat(),
            "summary": {
                "total_files": total_files,
                "total_lines": total_lines,
                "code_lines": total_code,
                "comment_lines": total_comment,
                "blank_lines": total_blank,
                "comment_ratio": round(total_comment / max(total_code, 1) * 100, 1),
                "total_size_bytes": self.total_size,
                "total_size_human": self._human_size(self.total_size),
            },
            "languages": {
                LANGUAGES[ext]["name"]: {
                    "files": s["files"],
                    "code": s["code"],
                    "comment": s["comment"],
                    "blank": s["blank"],
                    "total": s["total"],
                }
                for ext, s in sorted(
                    self.stats.items(), key=lambda x: x[1]["code"], reverse=True
                )
            },
            "largest_files": sorted(
                self.all_files_data, key=lambda x: x["total"], reverse=True
            )[:self.top_n],
            "most_complex": sorted(
                self.complexity_scores, key=lambda x: x[1], reverse=True
            )[:self.top_n],
            "todos": self.todos[:50],
            "dependencies": self.get_dependencies(),
        }

    @staticmethod
    def _human_size(nbytes):
        if nbytes == 0:
            return "0 B"
        units = ["B", "KB", "MB", "GB"]
        i = int(math.floor(math.log(nbytes, 1024)))
        return f"{nbytes / (1024 ** i):.1f} {units[i]}"


# ── Terminal report renderer ──────────────────────────────────
class TerminalReport:
    def __init__(self, data):
        self.data = data

    def render(self):
        self._header()
        self._summary()
        self._languages()
        self._bar_chart()
        self._largest_files()
        self._complexity()
        self._todos()
        self._dependencies()
        self._footer()

    def _header(self):
        print()
        print(f"  {CYAN}{BOLD}DEVSCAN{RESET} {DIM}v{__version__}{RESET}")
        print(f"  {GRAY}{'=' * 56}{RESET}")
        print(f"  {WHITE}{BOLD}{self.data['project']}{RESET}")
        print(f"  {GRAY}{self.data['path']}{RESET}")
        print(f"  {GRAY}Scanned: {self.data['scanned_at'][:19]}{RESET}")
        print()

    def _summary(self):
        s = self.data["summary"]
        print(f"  {CYAN}{BOLD}OVERVIEW{RESET}")
        print(f"  {GRAY}{'.' * 56}{RESET}")

        items = [
            ("Files", f"{s['total_files']:,}"),
            ("Lines of Code", f"{s['code_lines']:,}"),
            ("Comments", f"{s['comment_lines']:,} ({s['comment_ratio']}%)"),
            ("Blank Lines", f"{s['blank_lines']:,}"),
            ("Total Lines", f"{s['total_lines']:,}"),
            ("Project Size", s["total_size_human"]),
        ]
        for label, value in items:
            print(f"  {WHITE}{label:<22}{RESET} {GREEN}{value}{RESET}")
        print()

    def _languages(self):
        print(f"  {CYAN}{BOLD}LANGUAGES{RESET}")
        print(f"  {GRAY}{'.' * 56}{RESET}")
        print(f"  {DIM}{'Language':<18} {'Files':>6} {'Code':>8} {'Comment':>8} {'Blank':>7}{RESET}")
        print(f"  {GRAY}{'-' * 50}{RESET}")

        total_code = self.data["summary"]["code_lines"]
        for name, info in self.data["languages"].items():
            pct = info["code"] / max(total_code, 1) * 100
            ext = next((e for e, l in LANGUAGES.items() if l["name"] == name), None)
            color = LANGUAGES[ext]["color"] if ext else WHITE
            print(
                f"  {color}{name:<18}{RESET} "
                f"{info['files']:>6} {info['code']:>8} "
                f"{info['comment']:>8} {info['blank']:>7} "
                f"{DIM}({pct:>5.1f}%){RESET}"
            )
        print()

    def _bar_chart(self):
        print(f"  {CYAN}{BOLD}CODE DISTRIBUTION{RESET}")
        print(f"  {GRAY}{'.' * 56}{RESET}")

        total_code = self.data["summary"]["code_lines"]
        max_bar = 40

        for name, info in list(self.data["languages"].items())[:8]:
            pct = info["code"] / max(total_code, 1)
            bar_len = int(pct * max_bar)
            ext = next((e for e, l in LANGUAGES.items() if l["name"] == name), None)
            color = LANGUAGES[ext]["color"] if ext else WHITE
            bar = "█" * bar_len + "░" * (max_bar - bar_len)
            print(f"  {color}{name:<14}{RESET} {color}{bar}{RESET} {pct*100:>5.1f}%")
        print()

    def _largest_files(self):
        print(f"  {CYAN}{BOLD}LARGEST FILES{RESET}")
        print(f"  {GRAY}{'.' * 56}{RESET}")

        for f in self.data["largest_files"][:10]:
            size = f["total"]
            path = f["path"]
            if len(path) > 42:
                path = "..." + path[-39:]
            print(f"  {YELLOW}{size:>6}{RESET} lines  {WHITE}{path}{RESET}")
        print()

    def _complexity(self):
        print(f"  {CYAN}{BOLD}HIGHEST COMPLEXITY{RESET}")
        print(f"  {GRAY}{'.' * 56}{RESET}")

        for path, score, lines in self.data["most_complex"][:10]:
            if score == 0:
                continue
            if len(path) > 38:
                path = "..." + path[-35:]
            ratio = score / max(lines, 1)
            color = RED if ratio > 0.15 else YELLOW if ratio > 0.08 else GREEN
            print(
                f"  {color}{score:>5}{RESET} branches  "
                f"{DIM}({ratio:.2f}/line){RESET}  {WHITE}{path}{RESET}"
            )
        print()

    def _todos(self):
        if not self.data["todos"]:
            return
        print(f"  {CYAN}{BOLD}TODO / FIXME / HACK{RESET}")
        print(f"  {GRAY}{'.' * 56}{RESET}")

        for path, line_num, text in self.data["todos"][:10]:
            if len(path) > 30:
                path = "..." + path[-27:]
            print(f"  {MAGENTA}{path}:{line_num}{RESET}")
            print(f"    {DIM}{text}{RESET}")
        if len(self.data["todos"]) > 10:
            print(f"  {GRAY}  ... and {len(self.data['todos']) - 10} more{RESET}")
        print()

    def _dependencies(self):
        deps = self.data["dependencies"]
        if not deps:
            return
        print(f"  {CYAN}{BOLD}DEPENDENCIES{RESET}")
        print(f"  {GRAY}{'.' * 56}{RESET}")

        for manager, info in deps.items():
            parts = [f"{k}: {v}" for k, v in info.items()]
            print(f"  {WHITE}{manager}{RESET}  {DIM}{', '.join(parts)}{RESET}")
        print()

    def _footer(self):
        print(f"  {GRAY}{'=' * 56}{RESET}")
        print(f"  {DIM}devscan v{__version__} | github.com/TheSnatcher757/DevScan{RESET}")
        print()


# ── CLI entry point ───────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        prog="devscan",
        description="Analyze a codebase and generate a detailed report.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  devscan .                        Scan current directory\n"
            "  devscan /path/to/project         Scan a specific project\n"
            "  devscan . --format json           Output as JSON\n"
            "  devscan . --format json -o report.json\n"
            "  devscan . --ignore node_modules,dist --top 20\n"
        ),
    )
    parser.add_argument(
        "path", nargs="?", default=".",
        help="Path to the project directory (default: current dir)",
    )
    parser.add_argument(
        "--format", "-f", choices=["terminal", "json"], default="terminal",
        help="Output format (default: terminal)",
    )
    parser.add_argument(
        "--output", "-o", type=str, default=None,
        help="Write output to file instead of stdout",
    )
    parser.add_argument(
        "--ignore", "-i", type=str, default=None,
        help="Comma-separated list of directories to ignore",
    )
    parser.add_argument(
        "--top", "-t", type=int, default=15,
        help="Number of items in top-N lists (default: 15)",
    )
    parser.add_argument(
        "--version", "-v", action="version", version=f"devscan {__version__}",
    )

    args = parser.parse_args()

    target = Path(args.path).resolve()
    if not target.is_dir():
        print(f"  {RED}Error: '{args.path}' is not a valid directory.{RESET}")
        sys.exit(1)

    ignore = DEFAULT_IGNORE.copy()
    if args.ignore:
        ignore.update(args.ignore.split(","))

    analyzer = CodeAnalyzer(target, ignore_dirs=ignore, top_n=args.top)
    analyzer.scan()
    data = analyzer.to_dict()

    if data["summary"]["total_files"] == 0:
        print(f"  {YELLOW}No recognized source files found in '{target}'.{RESET}")
        sys.exit(0)

    if args.format == "json":
        output = json.dumps(data, indent=2)
        if args.output:
            Path(args.output).write_text(output)
            print(f"  {GREEN}Report saved to {args.output}{RESET}")
        else:
            print(output)
    else:
        report = TerminalReport(data)
        report.render()


if __name__ == "__main__":
    main()
