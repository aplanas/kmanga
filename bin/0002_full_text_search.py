# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql='''
CREATE MATERIALIZED VIEW main_manga_fts_view AS
SELECT main_manga.id,
       setweight(to_tsvector(main_manga.name), 'A') ||
       to_tsvector(main_manga.description) ||
       to_tsvector(coalesce(string_agg(main_altname.name, ' '))) as document
FROM main_manga
JOIN main_altname ON main_manga.id = main_altname.manga_id
GROUP BY main_manga.id;

CREATE INDEX main_manga_fts_idx ON main_manga_fts_view USING gin(document);
''',
            reverse_sql='''
DROP INDEX main_manga_fts_idx;

DROP MATERIALIZED VIEW main_manga_fts_view;
'''
        )
    ]
