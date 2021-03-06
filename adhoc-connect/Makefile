TOP=..
SUBDIRS=
DISTDIR=${TOP}/dist/adhoc-connect
RELEASEDIR=${TOP}/releases
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
	mkdir -p ${DISTDIR} ${DISTDIR}/etc/cron.d ${DISTDIR}/sbin;\
	sed "s/@@ADHOC_RELEASE@@/$${revno}/" < ./sbin/adhoc-connect.sh | \
	sed "s/@@ADHOC_GIT_VERSION@@/$${git_version}/" > ${DISTDIR}/sbin/adhoc-connect.sh ;\
	sed "s/@@ADHOC_RELEASE@@/$${revno}/" < ./etc/cron.d/adhoc-connect | \
	sed "s/@@ADHOC_GIT_VERSION@@/$${git_version}/" > ${DISTDIR}/etc/cron.d/adhoc-connect; \
	chmod 544 ${DISTDIR}/sbin/adhoc-connect.sh; \
	cp ./INSTALL.txt ./fix-files-adhoc-connect.sh ${DISTDIR}; \
	chmod +x ${DISTDIR}/fix-files-adhoc-connect.sh;
	
release: install
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
	rm -rf ${DISTDIR}/../adhoc-connect-$${revno}; \
	cp ${DISTDIR}/INSTALL.txt ${RELEASEDIR}/INSTALL_adhoc_connect.txt ;\
	(cd ${DISTDIR}/..; \
	mv adhoc-connect adhoc-connect-$${revno}; \
	mtreefile=`mktemp -t mtree`; \
	echo '#mtree v1.0' >$$mtreefile; \
	echo "adhoc-connect-$${revno} uid=0 gid=0 mode=0755 type=dir" >>$$mtreefile ; \
	cat ${TOP}/adhoc-connect/dist.mtree >>$$mtreefile ;\
	tar cf ${RELEASEDIR}/adhoc-connect-$${revno}.tar @$$mtreefile; rm -f $$mtreefile )

patchbump:
	(patch=`cat rel_patch`; patch=`expr $${patch} + 1`; echo $${patch} > rel_patch)
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
	git commit rel_patch -m "Bumped patch version to $${revno}"

minorbump:
	(minor=`cat rel_minor`; minor=`expr $${minor} + 1`; echo $${minor} > rel_minor; echo 0 > rel_patch)
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
	git commit rel_minor rel_patch -m "Bumped minor version to $${revno}"

majorbump:
	(major=`cat rel_major`; major=`expr $${major} + 1`; echo $${major} > rel_major; echo 0 > rel_minor; echo 0 > rel_patch)
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
	git commit rel_major rel_minor rel_patch -m "Bumped major version to $${revno}"

gitstatus:
	if git status -s | awk '{print $$1" "$$2}' | grep -v '\.\./' | grep -v Makefile | egrep "A|M|\?\?" >/dev/null ; then \
	    echo "There are untracked or uncommitted new or modified files in adhoc-connect, please commit first";\
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
			echo "Release number for adhoc-connect needs to be bumped"; \
			false; \
		    fi \
		fi \
	    fi \
	fi

gitmajor:
	git_version=`git rev-list --max-count=1 HEAD`;\
