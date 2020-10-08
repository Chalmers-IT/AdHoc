TOP=../..
SUBDIRS=
DISTDIR=${TOP}/dist/adhoc-scripts
RELEASEDIR=${TOP}/releases
RPCC_DIR=${TOP}/RPCC/client_libs

subdirs:
	for dir in $(SUBDIRS); do \
	    TOP=${TOP} $(MAKE) -e -C $$dir ${MAKEFLAGS} ;\
	done

clean:
	rm -rf ${DISTDIR}
	for dir in $(SUBDIRS); do \
	    TOP=${TOP} $(MAKE) -e -C $$dir ${MAKEFLAGS}  clean;\
	done

install: clean
	for dir in $(SUBDIRS); do \
	    TOP=${TOP} $(MAKE) -e -C $$dir ${MAKEFLAGS}  install;\
	done
	
	git_version=`git rev-list --max-count=1 HEAD`;\
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
	mkdir -p ${DISTDIR};\
	cp adhoc adhoc2 adhoc-test main.py ${RPCC_DIR}/rpcc_client.py ${DISTDIR};\
	(cd ${DISTDIR}; chmod +x adhoc adhoc2 adhoc-test ) ;\
	(cd ${DISTDIR}; find . -name \*.pyc -exec rm {} \;)

release: gitstatus install
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
	(cd ${DISTDIR}/..; mv adhoc-scripts adhoc-scripts-$${revno};/usr/local/bin/gtar cf ${RELEASEDIR}/adhoc-scripts-$${revno}.tar adhoc-scripts-$${revno};)
	
patch: gitstatus patchbump install

minor: gitstatus minorbump install

major: gitstatus majorbump install

patchbump:
	(patch=`cat rel_patch`; patch=`expr $${patch} + 1`; echo $${patch} > rel_patch)
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
	git commit rel_patch -*m "Bumped patch version to $${revno}"
	git tag -a -m "Bumped a patch release" $${revno} ;\
        git push --follow-tags

minorbump:
	(minor=`cat rel_minor`; minor=`expr $${minor} + 1`; echo $${minor} > rel_minor; echo 0 > rel_patch)
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
	git commit rel_minor rel_patch -m "Bumped minor version to $${revno}"
	git tag -a -m "Bumped a minor release" $${revno} ;\
	git push --follow-tags

majorbump:
	(major=`cat rel_major`; major=`expr $${major} + 1`; echo $${major} > rel_major; echo 0 > rel_minor; echo 0 > rel_patch)
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
	git commit rel_major rel_minor rel_patch -m "Bumped major version to $${revno}"
	git tag -a -m "Bumped a major release" $${revno} ;\
	git push --follow-tags

nobump:
	(patch=`cat rel_patch`; patch=`expr $${patch} + 1`; echo $${patch} > rel_patch)
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
	(patch=`cat rel_patch`; patch=`expr $${patch} - 1`; echo $${patch} > rel_patch)
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
        git tag -f -a -m "Re-bumped a patch release" $${revno} ;\
        git push --follow-tags

gitstatus:
	if git status -s | awk '{print $$1" "$$2}' | grep -v '\.\./' | grep -v Makefile | egrep "A|M|\?\?" >/dev/null ; then \
	    echo "There are untracked or uncommitted new or modified files in dhconf, please commit first";\
	    false ; \
	else \
	    git_version=`git rev-list --max-count=1 HEAD .`;\
	    if [ `git rev-list --max-count=1 HEAD rel_patch` =  $${git_version} ]; then \
		true; \
	    else \
		if [ `git rev-list --max-count=1 HEAD rel_minor` = $${git_version} ]; then \
			true; \
		else \
		    if [ `git rev-list --max-count=1 HEAD rel_major` = $${git_version} ]; then \
			true; \
		    else \
			echo "Release number for dhconf needs to be bumped"; \
			false; \
		    fi \
		fi \
	    fi \
	fi
