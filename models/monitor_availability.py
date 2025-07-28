from odoo import models, fields, api
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError
import calendar

class MonitorAvailability(models.Model):
    """Disponibilité des moniteurs"""
    _name = "monitor.availability"
    _description = "Disponibilité moniteur"
    _order = "date_from desc"

    monitor_id = fields.Many2one(
        'res.partner',
        string="Moniteur",
        domain="[('is_monitor', '=', True)]",
        required=True
    )
    
    date_from = fields.Date(string="Du", required=True)
    date_to = fields.Date(string="Au", required=True)
    
    availability_type = fields.Selection([
        ('available', 'Disponible'),
        ('unavailable', 'Indisponible'),
        ('limited', 'Disponibilité limitée')
    ], string="Type", required=True, default='available')
    
    reason = fields.Text(string="Raison")
    
    # Pour disponibilité limitée
    available_days = fields.Selection([
        ('monday', 'Lundi'),
        ('tuesday', 'Mardi'),
        ('wednesday', 'Mercredi'),
        ('thursday', 'Jeudi'),
        ('friday', 'Vendredi'),
        ('saturday', 'Samedi'),
        ('sunday', 'Dimanche')
    ], string="Jours disponibles")
    
    available_time_from = fields.Float(string="Disponible de")
    available_time_to = fields.Float(string="Disponible jusqu'à")
    
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for availability in self:
            if availability.date_from > availability.date_to:
                raise ValidationError("La date de début doit être antérieure à la date de fin.")
    
    @api.constrains('available_time_from', 'available_time_to')
    def _check_times(self):
        for availability in self:
            if (availability.availability_type == 'limited' and 
                availability.available_time_from and availability.available_time_to and
                availability.available_time_from >= availability.available_time_to):
                raise ValidationError("L'heure de début doit être antérieure à l'heure de fin.")