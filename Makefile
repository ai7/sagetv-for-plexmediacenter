######################################################################
# simple makefile for sagetv-for-plexmediacenter
######################################################################

# dependency specification

SRC_DIR = src
BUILD_DIR = build
STAGE_DIR = $(BUILD_DIR)/stage

SCANNER_TV    = $(STAGE_DIR)/plex/Scanners/Series
SCANNER_MOVIE = $(STAGE_DIR)/plex/Scanners/Movies
AGENT_DIR     = $(STAGE_DIR)/plex/Plug-ins

AGENT_COMMON  = plexlog.py config.py sagex.py

all: sagex scanner agent zip

######################################################################

# simple makefile rules that copies files to the correct folder
# location for easy install on target machine

sagex:
	@echo "*** building sagex ***"
	mkdir -p $(STAGE_DIR)/sagetv/sagex/services
	cp $(SRC_DIR)/sagetv/sagex-services/plex.js $(STAGE_DIR)/sagetv/sagex/services

scanner:
	@echo "*** building scanners ***"
	mkdir -p $(SCANNER_TV)/sageplex
	mkdir -p $(SCANNER_MOVIE)/sageplex
	# copy main scanner
	cp "$(SRC_DIR)/plex/scanner/SageTV Scanner.py" "$(SCANNER_TV)"
	cp "$(SRC_DIR)/plex/scanner/SageTV Movie Scanner.py" "$(SCANNER_MOVIE)"
	# copy library to each scanner's sub folder
	cp -r $(SRC_DIR)/plex/common/sageplex "$(SCANNER_TV)"
	cp -r $(SRC_DIR)/plex/common/sageplex "$(SCANNER_MOVIE)"
	# copy config file
	cp $(SRC_DIR)/plex/sageplex_cfg.json $(STAGE_DIR)/plex

agent:
	@echo "*** building agents ***"
	mkdir -p $(AGENT_DIR)
	# copy main agent folder
	cp -r $(SRC_DIR)/plex/agent/BMTAgentTVShows.bundle $(AGENT_DIR)
	# copy common code individually (skip __init__.py)
	for f in $(AGENT_COMMON); do \
	  cp $(SRC_DIR)/plex/common/sageplex/$$f \
	    "$(AGENT_DIR)/BMTAgentTVShows.bundle/Contents/Code"; \
        done

zip:
	@echo "*** producing zipfile ***"
	cd $(STAGE_DIR) && zip -9rX ../sagetv-for-plexmediacenter-r8.zip .

clean:
	rm -rf $(BUILD_DIR)

######################################################################

# phony targets are unaffected by files with the same name
.PHONY : all clean sagex scanner agent zip
