
.SUFFIXES :
include ../../INSTALL

LANG := $(notdir $(CURDIR))
XML_DIR_ := $(DESTDIR)$(helpdir)/meld/$(LANG)
OMF_NAME := meld-$(LANG).omf
OMF_DIR_ := $(DESTDIR)$(sharedir)/omf/meld
OMF_STATE:= $(DESTDIR)$(localstatedir)/lib/scrollkeeper
INST_XML := $(helpdir_)/$(LANG)/meld.xml

.PHONY : all
all $(OMF_NAME).install : $(OMF_NAME)
	scrollkeeper-preinstall $(INST_XML) $(OMF_NAME) $(OMF_NAME).install

.PHONY : install
install : $(OMF_NAME).install
	-mkdir -m 755 -p $(OMF_DIR_) $(XML_DIR_) $(XML_DIR_)/figures
	install -m 644 meld.$(LANG).xml $(XML_DIR_)/meld.xml
	install -m 644 figures/*.png $(XML_DIR_)/figures
	-install -m 644 $< $(OMF_DIR_)/$(OMF_NAME)
	-scrollkeeper-update -p $(OMF_STATE) -o $(OMF_DIR_)

.PHONY : uninstall
uninstall :
	-rm -f $(OMF_DIR_)/$(OMF_NAME) \
		$(XML_DIR_)/meld.xml \
		$(XML_DIR_)/figures/*.png
	-rmdir $(XML_DIR_)/figures \
		$(XML_DIR_)
	-scrollkeeper-update -p $(OMF_STATE) -o $(OMF_DIR_)

.PHONY : clean
clean :
	-rm -f $(OMF_NAME).install

