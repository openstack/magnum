step="enable-ingress-controller"
printf "Starting to run ${step}\n"

. /etc/sysconfig/heat-params

function writeFile {
    # $1 is filename
    # $2 is file content

    [ -f ${1} ] || {
        echo "Writing File: $1"
        mkdir -p $(dirname ${1})
        cat << EOF > ${1}
$2
EOF
    }
}

ingress_controller=$(echo $INGRESS_CONTROLLER | tr '[:upper:]' '[:lower:]')
case "$ingress_controller" in
"")
    echo "No ingress controller configured."
    ;;
"traefik")
    $enable-ingress-traefik
    ;;
"octavia")
    $enable-ingress-octavia
    ;;
*)
    echo "Ingress controller $ingress_controller not supported."
    ;;
esac

printf "Finished running ${step}\n"
