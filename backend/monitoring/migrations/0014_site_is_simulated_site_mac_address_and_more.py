from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitoring', '0013_cablehealthtelemetry'),
    ]

    operations = [
        migrations.AddField(
            model_name='site',
            name='mac_address',
            field=models.CharField(
                blank=True,
                help_text='MAC Address ESP32 (contoh: 3A:0E:4C:1E:80:6E)',
                max_length=50,
                null=True
            ),
        ),
        migrations.AddField(
            model_name='site',
            name='is_simulated',
            field=models.BooleanField(
                default=True,
                help_text='Apakah simulasi dummy aktif untuk site ini? (Matikan jika sudah menggunakan alat fisik)'
            ),
        ),
        migrations.CreateModel(
            name='VerticalitySimulatorConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_master_enabled', models.BooleanField(default=True, help_text='Master switch: Hidupkan/matikan seluruh simulator dummy verticality')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Verticality Simulator Config',
                'verbose_name_plural': 'Verticality Simulator Configs',
            },
        ),
    ]
