    IMG=""
    TAG=""

    yml=ixiatg-configmap.yaml
    echo "Loading container images for Ixia-c"

    while read line
    do
        if [ -z "${IMG}" ]
        then
            IMG=$(echo "$line" | grep path | cut -d\" -f4)
        elif [ -z "${TAG}" ]
        then
            TAG=$(echo "$line" | grep tag | cut -d\" -f4)
        else
            PTH="$IMG:$TAG"
            IMG=""
            TAG=""

            echo "Loading $PTH"
            docker pull $PTH
            kind load docker-image $PTH --name kne
        fi
    done <${yml}
