# -*- coding: utf-8 -*-
"""
Radicale 3.x rights plugin.

Ports the old ``DJRADICALE_RIGHTS`` policy: an authenticated user may read and
write only collections/items below their own principal (``{login}/...``) and
their own principal root (``{login}``). Everything else is denied.

``authorization`` returns a permission string built from the letters
``R`` (read collection), ``r`` (read item), ``W`` (write collection),
``w`` (write item). See Radicale's rights documentation.
"""
from radicale.rights import BaseRights


class Rights(BaseRights):
    def authorization(self, user, path):
        if not user:
            return ""
        sane = path.strip("/")
        if not sane:
            # The discovery root — allow read so clients can resolve the
            # current-user-principal.
            return "R"
        owner = sane.split("/", 1)[0]
        if owner == user:
            return "RrWw"
        return ""
