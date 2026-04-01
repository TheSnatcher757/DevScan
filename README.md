[README (1).md](https://github.com/user-attachments/files/26413948/README.1.md)
# DevScan - Codebase Analyzer CLI

A command-line tool that scans project directories and generates detailed reports on code structure, complexity, dependencies, and quality metrics. Instantly understand any codebase.

## Features

- Language detection and line counting (code, comments, blanks) across 25+ languages
- Visual bar chart showing code distribution by language
- Cyclomatic complexity estimation per file
- Largest files ranking
- TODO/FIXME/HACK tracker with file locations
- Dependency analysis (npm, pip, cargo, go modules)
- Terminal output with color-coded formatting
- JSON export for CI/CD integration
- Configurable directory ignore list

## Installation

```bash
git clone https://github.com/TheSnatcher757/DevScan.git
cd DevScan
chmod +x devscan.py

# Optional: add to PATH
cp devscan.py ~/.local/bin/devscan
```

No external dependencies. Runs on Python 3.7+ standard library only.

## Usage

```bash
# Scan current directory
python devscan.py .

# Scan a specific project
python devscan.py /path/to/project

# Export as JSON
python devscan.py . --format json

# Save report to file
python devscan.py . --format json -o report.json

# Custom ignore and top-N
python devscan.py . --ignore node_modules,dist,coverage --top 20
```

## Example Output

```
  DEVSCAN v1.2.0
  ========================================================
  my-react-app
  /home/user/projects/my-react-app

  OVERVIEW
  ........................................................
  Files                  47
  Lines of Code          3,842
  Comments               312 (8.1%)
  Blank Lines            489
  Total Lines            4,643
  Project Size           142.3 KB

  LANGUAGES
  ........................................................
  Language           Files     Code  Comment    Blank
  --------------------------------------------------
  TypeScript            18    2,104      198      267 ( 54.8%)
  React TSX             12    1,203       84      142 ( 31.3%)
  CSS                    8      312       18       52 (  8.1%)
  JSON                   5      180        0       12 (  4.7%)
  Markdown               4       43       12       16 (  1.1%)

  CODE DISTRIBUTION
  ........................................................
  TypeScript     ██████████████████████░░░░░░░░░░░░░░░░░░░  54.8%
  React TSX      ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░  31.3%
  CSS            ███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   8.1%
  JSON           ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   4.7%
```

## Supported Languages

Python, JavaScript, TypeScript, React (JSX/TSX), Java, C, C++, Rust, Go, Ruby, PHP, Swift, Kotlin, R, HTML, CSS, SCSS, SQL, Shell, YAML, JSON, Markdown, XML

## Options

| Flag | Description |
|---|---|
| `path` | Directory to scan (default: `.`) |
| `--format, -f` | Output format: `terminal` or `json` |
| `--output, -o` | Write to file instead of stdout |
| `--ignore, -i` | Comma-separated dirs to skip |
| `--top, -t` | Items in top-N lists (default: 15) |
| `--version, -v` | Show version |

## License

MIT License

## Author

**Angel Nunez Garcia**
B.S. Computer Science, San Diego State University
