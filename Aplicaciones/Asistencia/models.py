from django.db import models
from django.utils import timezone

class Empleado(models.Model):
    cedula = models.CharField(max_length=10, unique=True, verbose_name="Cédula")
    nombres = models.CharField(max_length=100, verbose_name="Nombres")
    apellidos = models.CharField(max_length=100, verbose_name="Apellidos")
    cargo = models.CharField(max_length=100, verbose_name="Cargo")
    telefono = models.CharField(max_length=10, verbose_name="Teléfono")
    email = models.EmailField(blank=True, null=True, verbose_name="Correo Electrónico")
    fecha_ingreso = models.DateField(verbose_name="Fecha de Ingreso")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    
    class Meta:
        verbose_name = "Empleado"
        verbose_name_plural = "Empleados"
        ordering = ['apellidos', 'nombres']
    
    def __str__(self):
        return f"{self.apellidos} {self.nombres}"
    
    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}"


class Asistencia(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='asistencias')
    fecha = models.DateField(default=timezone.now, verbose_name="Fecha")
    hora_entrada = models.TimeField(verbose_name="Hora de Entrada")
    hora_salida = models.TimeField(null=True, blank=True, verbose_name="Hora de Salida")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    
    class Meta:
        verbose_name = "Asistencia"
        verbose_name_plural = "Asistencias"
        ordering = ['-fecha', '-hora_entrada']
        unique_together = ['empleado', 'fecha']
    
    def __str__(self):
        return f"{self.empleado.nombre_completo} - {self.fecha}"
    
    @property
    def registro_completo(self):
        return bool(self.hora_salida)
    
    def duracion_jornada(self):
        if not self.hora_salida:
            return "Pendiente"
        from datetime import datetime, timedelta
        entrada = datetime.combine(self.fecha, self.hora_entrada)
        salida = datetime.combine(self.fecha, self.hora_salida)
        if salida < entrada:
            salida += timedelta(days=1)
        duracion = salida - entrada
        horas = int(duracion.total_seconds() // 3600)
        minutos = int((duracion.total_seconds() % 3600) // 60)
        return f"{horas}h {minutos}m"