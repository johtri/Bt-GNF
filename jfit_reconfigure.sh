pid=`ps -ef | grep ".*main.py" | grep -v 'grep' | awk '{ print $1}'` && \
            kill -s HUP $pid

