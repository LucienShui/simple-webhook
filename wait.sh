#!/usr/bin/env bash
TMP_FILE=$(mktemp)
NAME="${1}"
SECRET="${2}"

trap "rm -f ${TMP_FILE}" EXIT

until curl -o /dev/null -s -w "%{http_code}\n" "localhost:8000/api/status?name=${NAME}" -H "Authorization: ${SECRET}" > "${TMP_FILE}" && date && cat "${TMP_FILE}" &&  grep -v 202 "${TMP_FILE}" > /dev/null; do sleep 1; done

if [[ "$(cat ${TMP_FILE})" == 200 ]]; then
	exit 0
else
	exit 1
fi

