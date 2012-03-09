> stable-req.txt; for a in requirements-d.txt requirements.txt requirements-c.txt; do pip freeze -r "$a" >> stable-req.txt; done
