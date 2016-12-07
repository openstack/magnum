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

ALLOWED_EXTRA_MISSING=0

show_diff () {
    head -1 $1
    diff -U 0 $1 $2 | sed 1,2d
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
find . -type f -name "*.pyc" -delete && python setup.py testr --coverage --testr-args="$*"
coverage report > $baseline_report
mv cover cover-master
cat $baseline_report
baseline_missing=$(awk 'END { print $3 }' $baseline_report)

# Checkout back and save coverage report
git checkout -

current_op_count=`grep "op\." -R magnum/db/sqlalchemy/alembic/versions/ | wc -l`
current_report=$(mktemp -t magnum_coverageXXXXXXX)
find . -type f -name "*.pyc" -delete && python setup.py testr --coverage --testr-args="$*"
coverage report > $current_report
current_missing=$(awk 'END { print $3 }' $current_report)

# Show coverage details
allowed_missing=$((baseline_missing+ALLOWED_EXTRA_MISSING+current_op_count-base_op_count))

echo "Allowed to introduce missing lines : ${ALLOWED_EXTRA_MISSING}"
echo "Missing lines in master            : ${baseline_missing}"
echo "Missing lines in proposed change   : ${current_missing}"

if [ $allowed_missing -ge $current_missing ]; then
    if [ $baseline_missing -lt $current_missing ]; then
        show_diff $baseline_report $current_report
        echo "We believe you can test your code with 100% coverage!"
    else
        echo "Thank you! You are awesome! Keep writing unit tests! :)"
    fi
    exit_code=0
else
    show_diff $baseline_report $current_report
    echo "Please write more unit tests, we must maintain our test coverage :( "
    exit_code=1
fi

rm $baseline_report $current_report
exit $exit_code
