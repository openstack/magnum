#!/bin/bash
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

ALLOWED_EXTRA_MISSING_PERCENT=5

show_diff () {
    result=`diff -U 0 $1 $2 | sed 1,2d`
    [[ -n "$result" ]] && head -1 $1 || echo "No diff to display"
    echo "$result"
}

if ! git diff --exit-code || ! git diff --cached --exit-code
then
    echo "There are uncommitted changes!"
    echo "Please clean git working directory and try again"
    exit 1
fi

# Checkout master and save coverage report
git checkout HEAD^

base_op_count=`grep "op\." -R magnum/db/sqlalchemy/alembic/versions/ | wc -l`
baseline_report=$(mktemp -t magnum_coverageXXXXXXX)
coverage erase
find . -type f -name "*.pyc" -delete
stestr run --no-subunit-trace $*
coverage combine
coverage report > $baseline_report
cat $baseline_report
coverage html -d cover-master
coverage xml -o cover-master/coverage.xml

# Checkout back and save coverage report
git checkout -

current_op_count=`grep "op\." -R magnum/db/sqlalchemy/alembic/versions/ | wc -l`
current_report=$(mktemp -t magnum_coverageXXXXXXX)
coverage erase
find . -type f -name "*.pyc" -delete
stestr run --no-subunit-trace $*
coverage combine
coverage report --fail-under=89 > $current_report
cat $current_report
coverage html -d cover
coverage xml -o cover/coverage.xml

# Show coverage details
show_diff $baseline_report $current_report > cover/coverage.diff
cat cover/coverage.diff
baseline_missing=$(awk 'END { print $3 }' $baseline_report)
current_missing=$(awk 'END { print $3 }' $current_report)
allowed_extra_missing=$((baseline_missing*ALLOWED_EXTRA_MISSING_PERCENT/100))
allowed_missing=$((baseline_missing+allowed_extra_missing+current_op_count-base_op_count))

echo "Allowed to introduce missing lines : ${allowed_extra_missing}"
echo "Missing lines in baseline          : ${baseline_missing}"
echo "Missing lines in proposed change   : ${current_missing}"

if [ $allowed_missing -ge $current_missing ]; then
    if [ $baseline_missing -lt $current_missing ]; then
        echo "We believe you can test your code with 100% coverage!"
    else
        echo "Thank you! You are awesome! Keep writing unit tests! :)"
    fi
    exit_code=0
else
    echo "Please write more unit tests, we must maintain our test coverage :( "
    exit_code=1
fi

rm $baseline_report $current_report
exit $exit_code
