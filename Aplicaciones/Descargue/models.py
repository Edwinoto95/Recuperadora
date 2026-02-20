from django.db import models
from django.utils import timezone


class Empresa(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name_plural = "Empresas"
        ordering = ['nombre']


class Producto(models.Model):
    CATEGORIA_CHOICES = [
        ('papel',     '🧻 Papel / Higiene'),
        ('alimentos', '🌾 Alimentos secos'),
        ('bebidas',   '🧃 Bebidas'),
        ('lacteos',   '🥛 Lácteos'),
        ('limpieza',  '🧹 Limpieza'),
        ('aceites',   '🫙 Aceites / Grasas'),
        ('snacks',    '🍪 Snacks / Confitería'),
        ('otros',     '📦 Otros'),
    ]
    nombre            = models.CharField(max_length=150)
    categoria         = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='otros')
    unidades_por_capa = models.PositiveIntegerField(default=8)
    capas_por_palet   = models.PositiveIntegerField(default=8)
    activo            = models.BooleanField(default=True)

    @property
    def unidades_palet_completo(self):
        return self.unidades_por_capa * self.capas_por_palet

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name_plural = "Productos"
        ordering = ['categoria', 'nombre']


class CierreDia(models.Model):
    ESTADO_CHOICES = [('abierto', 'Abierto'), ('cerrado', 'Cerrado')]

    fecha         = models.DateField(default=timezone.now, unique=True)
    estado        = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='abierto')
    hora_cierre   = models.DateTimeField(null=True, blank=True)
    total_palets  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    observaciones = models.TextField(blank=True)

    def recalcular(self):
        total = sum(
            item.palets_equivalentes
            for reg in self.registros.all()
            for item in reg.items.all()
        )
        self.total_palets = round(total, 2)
        self.save(update_fields=['total_palets'])

    def __str__(self):
        return f"Cierre {self.fecha} | {self.get_estado_display()}"

    class Meta:
        verbose_name = "Cierre de Día"
        verbose_name_plural = "Cierres de Día"
        ordering = ['-fecha']


class RegistroDescargue(models.Model):
    """Un registro = llegada de UN camión/chofer con uno o varios productos."""
    TIPO_CHOICES = [
        ('completo',   'Completo'),
        ('incompleto', 'Incompleto'),
        ('especial',   'Especial'),
    ]
    cierre            = models.ForeignKey(CierreDia, on_delete=models.CASCADE, related_name='registros')
    empresa           = models.ForeignKey(Empresa, on_delete=models.SET_NULL, null=True, blank=True, related_name='descargues')
    chofer_nombre     = models.CharField(max_length=100, default='')
    chofer_telefono   = models.CharField(max_length=20, default='')
    placa             = models.CharField(max_length=20, blank=True)
    tipo              = models.CharField(max_length=12, choices=TIPO_CHOICES, default='completo')
    observacion       = models.CharField(max_length=200, blank=True)
    hora              = models.DateTimeField(default=timezone.now)
    duracion_minutos  = models.PositiveIntegerField(default=30)
    hora_fin_estimada = models.DateTimeField(null=True, blank=True)

    @property
    def total_palets(self):
        return round(sum(i.palets_equivalentes for i in self.items.all()), 4)

    def save(self, *args, **kwargs):
        if self.duracion_minutos and self.hora:
            from datetime import timedelta
            self.hora_fin_estimada = self.hora + timedelta(minutes=self.duracion_minutos)
        super().save(*args, **kwargs)

    def __str__(self):
        emp = self.empresa.nombre if self.empresa else '—'
        return f"{emp} | {self.chofer_nombre} | {self.hora:%H:%M}"

    class Meta:
        verbose_name = "Registro de Descargue"
        verbose_name_plural = "Registros de Descargue"
        ordering = ['-hora']


class ItemDescargue(models.Model):
    """Un producto dentro de un registro. Un camión puede traer N productos."""
    registro         = models.ForeignKey(RegistroDescargue, on_delete=models.CASCADE, related_name='items')
    producto         = models.ForeignKey(Producto, on_delete=models.CASCADE)
    palets_completos = models.PositiveIntegerField(default=0)
    unidades_sueltas = models.PositiveIntegerField(default=0)

    @property
    def palets_equivalentes(self):
        total = float(self.palets_completos)
        upc = self.producto.unidades_palet_completo
        if self.unidades_sueltas > 0 and upc > 0:
            total += round(self.unidades_sueltas / upc, 4)
        return round(total, 4)

    def __str__(self):
        return f"{self.producto.nombre} — {self.palets_equivalentes} pal"

    class Meta:
        verbose_name = "Ítem de Descargue"
        verbose_name_plural = "Ítems de Descargue"