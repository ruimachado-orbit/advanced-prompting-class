PYTHON := python3

.PHONY: help app

help:
	@echo "Usage: make <wall>_<example>"
	@echo ""
	@echo "  Wall 1 - Inconsistent Outputs"
	@echo "    make 1_1  ->  1_broken_version.py"
	@echo "    make 1_2  ->  2_schema_version.py"
	@echo "    make 1_3  ->  3_with_validation_and_fallback.py"
	@echo "    make 1_4  ->  4_pydantic_validation.py"
	@echo ""
	@echo "  Wall 2 - Quality Plateau"
	@echo "    make 2_1  ->  1_single_shot.py"
	@echo "    make 2_2  ->  2_multi_step_delegation.py"
	@echo "    make 2_3  ->  3_parallel_delegation.py"
	@echo ""
	@echo "  Wall 3 - Consistency Crisis"
	@echo "    make 3_1  ->  1_generic_assistant.py"
	@echo "    make 3_2  ->  2_role_based_system.py"
	@echo "    make 3_3  ->  3_consistency_testing.py"
	@echo ""
	@echo "  End-to-End Bug Triage"
	@echo "    make e2e_1  ->  1_run_me.py"
	@echo "    make e2e_2  ->  2_the_patterns.py"
	@echo "    make e2e_ui ->  gradio_ui/app.py"
	@echo ""
	@echo "  Gradio App"
	@echo "    make app   ->  Launch the Bug Triage UI"

# Wall 1 - Inconsistent Outputs
1_1:
	$(PYTHON) wall_1_inconsistent_outputs/1_broken_version.py
1_2:
	$(PYTHON) wall_1_inconsistent_outputs/2_schema_version.py
1_3:
	$(PYTHON) wall_1_inconsistent_outputs/3_with_validation_and_fallback.py
1_4:
	$(PYTHON) wall_1_inconsistent_outputs/4_pydantic_validation.py

# Wall 2 - Quality Plateau
2_1:
	$(PYTHON) wall_2_quality_plateau/1_single_shot.py
2_2:
	$(PYTHON) wall_2_quality_plateau/2_multi_step_delegation.py
2_3:
	$(PYTHON) wall_2_quality_plateau/3_parallel_delegation.py

# Wall 3 - Consistency Crisis
3_1:
	$(PYTHON) wall_3_consistency_crisis/1_generic_assistant.py
3_2:
	$(PYTHON) wall_3_consistency_crisis/2_role_based_system.py
3_3:
	$(PYTHON) wall_3_consistency_crisis/3_consistency_testing.py

# End-to-End Bug Triage
e2e_1:
	$(PYTHON) end_to_end_bug_triage/1_run_me.py
e2e_2:
	$(PYTHON) end_to_end_bug_triage/2_the_patterns.py
e2e_ui:
	$(PYTHON) end_to_end_bug_triage/gradio_ui/app.py

# Gradio App
app:
	$(PYTHON) end_to_end_bug_triage/gradio_ui/app.py
