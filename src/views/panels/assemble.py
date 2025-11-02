from urwid import Edit, LineBox

from src.models.assemble import AssembleType, assemble
from src.models.state import state
from src.views.widgets.form import Form
from src.views.widgets.radio import RadioGroup

class AssemblePanel(Form):

    def __init__(self):
        grading_directory = LineBox(Edit(("header", "Grading directory\n\n"), state.grading_directory))
        assignment_sname = LineBox(Edit(("header", "Assignment short name\n\n"), state.assignment_sname))
        assemble_type = RadioGroup("Assemble type", AssembleType, AssembleType.FINAL)

        grid_elements = [
            {"grading_directory": grading_directory, "assignment_sname": assignment_sname},
            {"assemble_type": assemble_type},
        ]

        super().__init__("Assemble", grid_elements, assemble)
