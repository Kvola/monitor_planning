from odoo import models, fields, api
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError
import calendar

class MonitorRotationLine(models.Model):
    """Ligne de rotation des moniteurs"""
    _name = "monitor.rotation.line"
    _description = "Ligne de rotation des moniteurs"
    _order = "sequence, id"

    template_id = fields.Many2one(
        'monitor.planning.template',
        string="Modèle de planification",
        ondelete='cascade',
        required=True
    )
    
    sequence = fields.Integer(string="Séquence", default=10)
    
    monitor_id = fields.Many2one(
        'res.partner',
        string="Moniteur",
        domain="[('is_monitor', '=', True)]",
        required=True
    )
    
    active = fields.Boolean(string="Actif", default=True)
    
    # Statistiques
    planning_count = fields.Integer(
        string="Planifications assignées",
        compute="_compute_planning_count"
    )
    
    @api.depends('monitor_id', 'template_id')
    def _compute_planning_count(self):
        for line in self:
            if line.monitor_id and line.template_id:
                line.planning_count = self.env['monitor.planning'].search_count([
                    ('template_id', '=', line.template_id.id),
                    ('monitor_id', '=', line.monitor_id.id)
                ])
            else:
                line.planning_count = 0