from odoo import models, fields, api
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError
import calendar

class MonitorCertificate(models.Model):
    """Certificats des moniteurs"""
    _name = "monitor.certificate"
    _description = "Certificat moniteur"
    _order = "certificate_date desc"

    monitor_id = fields.Many2one(
        'res.partner',
        string="Moniteur",
        domain="[('is_monitor', '=', True)]",
        required=True
    )
    
    training_id = fields.Many2one(
        'monitor.training',
        string="Formation associée"
    )
    
    certificate_date = fields.Date(
        string="Date du certificat",
        required=True,
        default=fields.Date.today
    )
    
    certificate_type = fields.Selection([
        ('training', 'Formation'),
        ('competency', 'Compétence'),
        ('achievement', 'Récompense'),
        ('recognition', 'Reconnaissance')
    ], string="Type de certificat", required=True)
    
    name = fields.Char(string="Nom du certificat", required=True)
    description = fields.Text(string="Description")
    
    issued_by_id = fields.Many2one(
        'res.partner',
        string="Délivré par",
        default=lambda self: self.env.user.partner_id
    )
    
    expiry_date = fields.Date(string="Date d'expiration")
    is_expired = fields.Boolean(
        string="Expiré",
        compute="_compute_is_expired"
    )
    
    certificate_number = fields.Char(
        string="Numéro de certificat",
        readonly=True,
        copy=False
    )
    
    @api.depends('expiry_date')
    def _compute_is_expired(self):
        today = fields.Date.today()
        for certificate in self:
            certificate.is_expired = (
                certificate.expiry_date and 
                certificate.expiry_date < today
            )
    
    @api.model
    def create(self, vals):
        """Générer automatiquement un numéro de certificat"""
        if not vals.get('certificate_number'):
            vals['certificate_number'] = self._generate_certificate_number()
        return super().create(vals)
    
    def _generate_certificate_number(self):
        """Génère un numéro de certificat unique"""
        year = fields.Date.today().year
        sequence = self.env['ir.sequence'].next_by_code('monitor.certificate') or '001'
        return f"CERT-{year}-{sequence}"