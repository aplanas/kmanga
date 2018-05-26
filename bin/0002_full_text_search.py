from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql='''
CREATE MATERIALIZED VIEW core_manga_fts_view AS
                  SELECT core_manga.id,
                         core_manga.name,
                         core_manga.url,
                         setweight(to_tsvector(core_manga.name), 'A') ||
                         to_tsvector(core_source.name) ||
                         to_tsvector(core_source.spider) ||
                         to_tsvector(core_manga.description) ||
                         to_tsvector(
                           coalesce(string_agg(core_altname.name, ' '), '')
                         ) AS document
                    FROM core_manga
               LEFT JOIN core_altname ON core_manga.id = core_altname.manga_id
              INNER JOIN core_source ON core_manga.source_id = core_source.id
                GROUP BY core_manga.id,
                         core_source.id;

CREATE INDEX core_manga_fts_idx ON core_manga_fts_view USING gin(document);
''',
            reverse_sql='''
DROP INDEX core_manga_fts_idx;

DROP MATERIALIZED VIEW core_manga_fts_view;
'''
        )
    ]
