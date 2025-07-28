from odoo import models, fields, api
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError
import calendar

class MonitorTraining(models.Model):
    """Formation des moniteurs"""
    _name = "monitor.training"
    _description = "Formation moniteur"
    _order = "date desc"

    name = fields.Char(string="Nom de la formation", required=True)
    description = fields.Text(string="Description")
    
    date = fields.Date(string="Date", required=True)
    duration = fields.Float(string="Durée (heures)", required=True)
    
    trainer_id = fields.Many2one(
        'res.partner',
        string="Formateur",
        required=True
    )
    
    training_type = fields.Selection([
        ('initial', 'Formation initiale'),
        ('continuous', 'Formation continue'),
        ('specialized', 'Formation spécialisée'),
        ('refresher', 'Recyclage')
    ], string="Type de formation", required=True)
    
    # Participants
    participant_ids = fields.Many2many(
        'res.partner',
        'training_participant_rel',
        'training_id',
        'monitor_id',
        string="Participants",
        domain="[('is_monitor', '=', True)]"
    )
    
    participant_count = fields.Integer(
        string="Nombre de participants",
        compute="_compute_participant_count"
    )
    
    # Matériel et ressources
    materials = fields.Text(string="Matériel fourni")
    resources = fields.Text(string="Ressources recommandées")
    
    # Évaluation de la formation
    feedback_collected = fields.Boolean(string="Retours collectés")
    average_rating = fields.Float(string="Note moyenne")
    
    state = fields.Selection([
        ('planned', 'Planifiée'),
        ('in_progress', 'En cours'),
        ('completed', 'Terminée'),
        ('cancelled', 'Annulée')
    ], string="État", default='planned', required=True)
    
    @api.depends('participant_ids')
    def _compute_participant_count(self):
        for training in self:
            training.participant_count = len(training.participant_ids)
    
    def action_start_training(self):
        """Démarrer la formation"""
        self.ensure_one()
        if self.state == 'planned':
            self.state = 'in_progress'
    
    def action_complete_training(self):
        """Terminer la formation"""
        self.ensure_one()
        if self.state == 'in_progress':
            self.state = 'completed'
            # Créer des certificats pour les participants
            self._create_certificates()
    
    def _create_certificates(self):
        """Crée des certificats de formation pour les participants"""
        for participant in self.participant_ids:
            self.env['monitor.certificate'].create({
                'monitor_id': participant.id,
                'training_id': self.id,
                'certificate_date': fields.Date.today(),
                'certificate_type': 'training',
                'description': f"Certificat de participation à la formation : {self.name}"
            })