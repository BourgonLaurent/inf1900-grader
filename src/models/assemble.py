from enum import Enum, auto
import re
from csv import writer
from datetime import datetime
from decimal import Decimal
from io import StringIO
from statistics import mean, stdev

from src.models.clone import read_grading_info
from src.models.grade import generate_grading_file_name, get_teams_list
from src.models.validate import InvalidInput, ensure_grading_directory_exists, ensure_not_empty, time_format

class AssembleType(Enum):
    FINAL = auto()
    PREVIEW = auto()

def parse_grade(number: str) -> Decimal:
    return Decimal(number.strip().replace(',', '.'))


def sum_partial_grades(team: str, grade_file_path: str) -> Decimal:
    with open(grade_file_path, 'r') as f:
        grading_file_content = f.read()

    BASE_GRADE_REGEX = r"[^\d,.]*(\d*[.,]?[\d\s]*)/"
    PARTIAL_GRADE_REGEX = "Résultat partiel" + BASE_GRADE_REGEX

    try:
        raw_grades: list[str] = re.findall(PARTIAL_GRADE_REGEX, grading_file_content)
        total_grade: Decimal = sum((parse_grade(grade) for grade in raw_grades), start=Decimal(0))
    except Exception as e:
        raise InvalidInput(f"Missing or invalid partial grade for team {team}.") from e

    return total_grade


def write_total_grade(grade_file_path: str, grade: Decimal) -> None:
    with open(grade_file_path, 'r') as f:
        grading_file_content = f.read()

    TOTAL_STRING = "Total des points"
    grading_file_content = re.sub(f".*{TOTAL_STRING}.*", f"__{TOTAL_STRING}: {grade}/20__", grading_file_content)

    with open(grade_file_path, 'w') as f:
        f.write(grading_file_content)


def extract_total_grade(
    team: str,
    grading_directory: str,
    assignment_sname: str,
    assemble_type: AssembleType = AssembleType.FINAL,
) -> Decimal | None:
    repo_path = f"{grading_directory}/{team}"
    grade_file_path = f"{repo_path}/{generate_grading_file_name(assignment_sname)}"

    try:
        total_grade = sum_partial_grades(team, grade_file_path)
    except InvalidInput:
        if assemble_type is AssembleType.FINAL:
            raise

        return None

    write_total_grade(grade_file_path, total_grade)

    return total_grade


def add_grade_to_student_info(student_info: dict, grades_map: dict[str, Decimal]) -> dict:
    return {**student_info, "grade": grades_map[student_info["team"]]}


def write_grades_file(
    grading_directory: str,
    grades_map: dict,
    assignment_sname: str,
    assemble_type: AssembleType,
) -> None:
    info = read_grading_info(grading_directory)
    group_number = info["group_number"]

    csv_output = StringIO()
    csv_writer = writer(csv_output, delimiter=";")
    csv_writer.writerows(
        [
            ["Cours:", "INF1900"],
            ["Correcteur:", info["grader_name"]],
            ["Section:", group_number],
            ["Date:", datetime.now().strftime(time_format)],
            ["Travail:", assignment_sname],
            [],
            [
                "Moyenne:",
                mean(grades_map.values())
                if assemble_type is AssembleType.FINAL or len(grades_map) >= 1
                else "Données insuffisantes",
            ],
            [
                "Écart-type:",
                stdev(grades_map.values())
                if assemble_type is AssembleType.FINAL or len(grades_map) >= 2
                else "Données insuffisantes",
            ],
            [],
            ["Nom", "Prénom", "Équipe", "Note"],
            *[
                list(add_grade_to_student_info(student_info, grades_map).values())
                for student_info in info["students"]
                if student_info["team"] in grades_map
            ],
        ]
    )

    # Hack: replace dot decimals with comma decimals
    csv_output = csv_output.getvalue().replace(".", ",")

    grades_path = f"{grading_directory}/notes-inf1900-sect0{group_number}-{assignment_sname}.csv"

    if assemble_type is AssembleType.PREVIEW:
        grades_path += ".preview"

    with open(grades_path, 'w', newline='', encoding="utf-8") as csvfile:
        csvfile.write(csv_output)


def assemble(
    grading_directory: str,
    assignment_sname: str,
    assemble_type: AssembleType,
) -> None:
    ensure_grading_directory_exists(grading_directory)
    ensure_not_empty(assignment_sname, "Assignment short name")

    teams = get_teams_list(grading_directory)
    grades = {
        team: grade
        for team in teams
        if (
            grade := extract_total_grade(
                team,
                grading_directory,
                assignment_sname,
                assemble_type,
            )
        )
        is not None
    }
    write_grades_file(grading_directory, grades, assignment_sname, assemble_type)
