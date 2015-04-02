# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql='''
CREATE MATERIALIZED VIEW core_manga_fts_view AS
SELECT core_manga.id,
       setweight(to_tsvector(core_manga.name), 'A') ||
       to_tsvector(core_manga.description) ||
       to_tsvector(coalesce(string_agg(core_altname.name, ' '))) as document
FROM core_manga
JOIN core_altname ON core_manga.id = core_altname.manga_id
GROUP BY core_manga.id;

CREATE INDEX core_manga_fts_idx ON core_manga_fts_view USING gin(document);
''',
            reverse_sql='''
DROP INDEX core_manga_fts_idx;

DROP MATERIALIZED VIEW core_manga_fts_view;
'''
        )
    ]
