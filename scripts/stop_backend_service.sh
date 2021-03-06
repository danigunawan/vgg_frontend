#!/bin/bash

# Check the parameter to the script.
# The strings used as parameter should correspond to the
# engines short-name in the settings of visorgen
case "${1}" in
    text)
        ## Stop the text-backend engine ##

        GREP=$(ps -fe | grep "[v]gg_text_search")
        if [ "$GREP" ]; then
            SESSION=$(screen -ls | grep -o ".*.visorgen-text-backend-service")
            if [ "$SESSION" ]; then
                screen -X -S $SESSION quit
            fi
        fi
        pkill -9 -f 'python text_retrieval_backend.py'
    ;;
    cpuvisor-srv)
        ## Stop the cpuvisor-srv engine ##

        # stop cpuvisor_service

        GREP=$(ps -fe | grep "[c]puvisor_service")
        if [ "$GREP" ]; then
            SESSION=$(screen -ls | grep -o ".*.visorgen-cpuvisor-service")
            if [ "$SESSION" ]; then
                screen -X -S $SESSION quit
            fi
        fi
        pkill -9 -f 'cpuvisor_service'

        GREP=$(ps -fe | grep ".*[v]isorgen-backend-service.*")
        if [ "$GREP" ]; then
            SESSION=$(screen -ls | grep -o ".*.visorgen-backend-service")
            if [ "$SESSION" ]; then
                screen -X -S $SESSION quit
            fi
        fi
        pkill -9 -f 'python legacy_serve.py'

        # stop image downloader tool
        GREP=$(ps -fe | grep "[a]pi_v2")
        if [ "$GREP" ]; then
            echo "instances engine still running, cannot stop image downloader"
        else
            GREP=$(ps -fe | grep ".*[v]isorgen-faces-backend-service.*")
            if [ "$GREP" ]; then
                echo "faces engine still running, cannot stop image downloader"
            else
                GREP=$(ps -fe | grep ".*[v]isorgen-img_downloader")
                if [ "$GREP" ]; then
                    SESSION=$(screen -ls | grep -o ".*.visorgen-img_downloader")
                    if [ "$SESSION" ]; then
                        screen -X -S $SESSION quit
                    fi
                fi
                pkill -9 -f 'imsearch_http_service.py'
            fi
        fi
    ;;
    faces)
        ## Stop the faces engine ##

        # stop faces backend

        GREP=$(ps -fe | grep ".*[v]isorgen-faces-backend-service.*")
        if [ "$GREP" ]; then
            SESSION=$(screen -ls | grep -o ".*.visorgen-faces-backend-service")
            if [ "$SESSION" ]; then
                screen -X -S $SESSION quit
            fi
        fi
        pkill -9 -f 'python backend.py'
    ;;
    instances)
        ## Stop the instances engine ##

        # stop the instance backend engines

        GREP=$(ps -fe | grep "[a]pi_v2")
        if [ "$GREP" ]; then
            SESSION=$(screen -ls | grep -o ".*.visorgen-instance-apiv2-service")
            if [ "$SESSION" ]; then
                screen -X -S $SESSION quit
            else
                kill -9 $(ps -fe | grep "[a]pi_v2" | awk '{print $2}')
            fi
        fi

        GREP=$(ps -fe | grep ".*[v]isorgen-instance-backend-service.*")
        if [ "$GREP" ]; then
            SESSION=$(screen -ls | grep -o ".*.visorgen-instance-backend-service")
            if [ "$SESSION" ]; then
                screen -X -S $SESSION quit
            fi
        fi
        pkill -9 -f 'python rr_visor_backend.py'

        # stop image downloader tool
        GREP=$(ps -fe | grep ".*[v]isorgen-faces-backend-service.*")
        if [ "$GREP" ]; then
            echo "faces engine still running, cannot stop image downloader"
        else
            GREP=$(ps -fe | grep "[c]puvisor_service")
            if [ "$GREP" ]; then
                echo "cpuvisor-srv engine still running, cannot stop image downloader"
            else
                GREP=$(ps -fe | grep ".*[v]isorgen-img_downloader")
                if [ "$GREP" ]; then
                    SESSION=$(screen -ls | grep -o ".*.visorgen-img_downloader")
                    if [ "$SESSION" ]; then
                        screen -X -S $SESSION quit
                    fi
                fi
                pkill -9 -f 'imsearch_http_service.py'
            fi
        fi
    ;;
    *)
        echo "Usage: ${0} {text|cpuvisor-srv|faces|instances}" >&2
    ;;
esac

exit 0
