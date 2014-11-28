# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


class CrudMixin(object):

    @classmethod
    def get_by_id(cls, context, id):
        """Return a specific object by its unique identifier."""

    @classmethod
    def get_by_uuid(cls, context, item_uuid):
        """Return a specific object by its uuid."""

    def create(self, context):
        """Create the model."""

    def save(self, context):
        """Change the model."""

    def destroy(self, context):
        """Destroy the model."""

    def add_forward_schema_changes(self):
        """Update the attributes of self to include new schema elements.

        This method is invoked during save/create operations to guarantee
        that objects being created during a schema transition support both
        new and old schemas.  This ensures that background jobs can run
        to migrate existing objects on a live system while writes are
        occurring.

        The changes made by this method must match the schema defined
        for "transitioning" and "new" (see solum.objects.__init__).
        """


class CrudListMixin(object):
    @classmethod
    def get_all(cls, context):
        """Retrieve all applications for the active context.

        Context may be global or tenant scoped.
        """
