SKILL_NAME := marimo-data-analysis
DEST := $(HOME)/.claude/skills/$(SKILL_NAME)

.PHONY: install
install: ## Copy skill/ into ~/.claude/skills for local testing in Claude Code
	mkdir -p $(DEST)
	rsync -a --delete --exclude '__pycache__' skill/ $(DEST)/
	@echo "Installed to $(DEST). Restart Claude Code (or start a new session) to pick it up."
