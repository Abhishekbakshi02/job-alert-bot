"""
Renders resume content into a PDF via LaTeX (xelatex), using a Jinja2
template with LaTeX-safe delimiters (\\VAR{...}, \\BLOCK{...} instead of
Jinja2's default {{ }} / {% %}, which would clash with LaTeX's own {}
syntax). All dynamic text is escaped BEFORE reaching the template, so
LaTeX special characters (&, %, $, #, _, {, }, ~, ^, \\) in AI-generated
content can never break the compile.
"""

import os
import shutil
import subprocess
import tempfile

from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_NAME = "resume_template.tex.jinja"

_LATEX_SPECIAL_CHARS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def _latex_escape(value) -> str:
    if value is None:
        return ""
    text = str(value)
    text = text.replace("\\", _LATEX_SPECIAL_CHARS["\\"])
    for char, repl in _LATEX_SPECIAL_CHARS.items():
        if char != "\\":
            text = text.replace(char, repl)
    return text


def _escape_deep(data):
    if isinstance(data, dict):
        return {k: _escape_deep(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_escape_deep(v) for v in data]
    if isinstance(data, str):
        return _latex_escape(data)
    return data


def _get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        block_start_string=r"\BLOCK{",
        block_end_string="}",
        variable_start_string=r"\VAR{",
        variable_end_string="}",
        comment_start_string=r"\#{",
        comment_end_string="}",
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
    )


def render_resume(data: dict, output_path: str) -> None:
    escaped = _escape_deep(data)
    env = _get_jinja_env()
    template = env.get_template(TEMPLATE_NAME)

    tex_source = template.render(
        name=escaped["name"],
        email=escaped["contact"]["email"],
        linkedin=escaped["contact"]["linkedin_label"],
        phone=escaped["contact"]["phone"],
        location=escaped["contact"]["location"],
        summary=escaped["summary"],
        skills=escaped["skills"],
        experience=escaped["experience"],
        projects=escaped["projects"],
        education=escaped["education"],
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "resume.tex")
        with open(tex_path, "w") as f:
            f.write(tex_source)

        result = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error", "resume.tex"],
            cwd=tmpdir, capture_output=True, text=True, timeout=60,
        )
        pdf_path = os.path.join(tmpdir, "resume.pdf")
        if result.returncode != 0 or not os.path.exists(pdf_path):
            raise RuntimeError(f"LaTeX compilation failed:\n{result.stdout[-2000:]}")

        shutil.copy(pdf_path, output_path)
