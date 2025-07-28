from odoo import models, fields, api
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError
import calendar

class MonitorPlanning(models.Model):
    """Planification d'intervention d'un moniteur"""
    _name = "monitor.planning"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Planification moniteur"
    _order = "planned_date desc, start_time"
    _rec_name = "display_name"

    name = fields.Char(string="Nom", required=True)
    
    # Relations
    template_id = fields.Many2one(
        'monitor.planning.template',
        string="Modèle de planification",
        ondelete='cascade'
    )
    
    school_id = fields.Many2one(
        'res.partner',
        string="École",
        domain="[('organization_type', '=', 'school')]",
        required=True
    )
    
    monitor_id = fields.Many2one(
        'res.partner',
        string="Moniteur assigné",
        domain="[('is_monitor', '=', True)]",
        required=True
    )
    
    substitute_monitor_id = fields.Many2one(
        'res.partner',
        string="Moniteur remplaçant",
        domain="[('is_monitor', '=', True)]",
        help="Moniteur qui interviendra à la place du moniteur principal"
    )
    
    # Planification
    planned_date = fields.Date(string="Date prévue", required=True)
    start_time = fields.Float(string="Heure de début", required=True)
    end_time = fields.Float(string="Heure de fin", required=True)
    
    # Contenu de l'intervention
    topic = fields.Char(string="Sujet/Thème")
    description = fields.Text(string="Description de l'intervention")
    target_age_group = fields.Char(string="Groupe d'âge ciblé")
    expected_participants = fields.Integer(string="Participants attendus")
    
    # Suivi
    state = fields.Selection([
        ('planned', 'Planifié'),
        ('confirmed', 'Confirmé'),
        ('in_progress', 'En cours'),
        ('completed', 'Terminé'),
        ('cancelled', 'Annulé'),
        ('postponed', 'Reporté')
    ], string="État", default='planned', required=True)
    
    # Réalisation
    actual_start_time = fields.Float(string="Heure de début réelle")
    actual_end_time = fields.Float(string="Heure de fin réelle")
    actual_participants = fields.Integer(string="Participants réels")
    
    # Évaluation
    monitor_feedback = fields.Text(string="Retour du moniteur")
    supervisor_feedback = fields.Text(string="Retour du superviseur")
    rating = fields.Selection([
        ('1', 'Très insatisfaisant'),
        ('2', 'Insatisfaisant'),
        ('3', 'Correct'),
        ('4', 'Bien'),
        ('5', 'Excellent')
    ], string="Évaluation")
    
    # Champs calculés
    display_name = fields.Char(string="Nom d'affichage", compute="_compute_display_name", store=True)
    duration_planned = fields.Float(string="Durée prévue (h)", compute="_compute_duration_planned", store=True)
    duration_actual = fields.Float(string="Durée réelle (h)", compute="_compute_duration_actual", store=True)
    is_overdue = fields.Boolean(string="En retard", compute="_compute_is_overdue", store=True)
    
    # Notification et rappels
    reminder_sent = fields.Boolean(string="Rappel envoyé", default=False)
    confirmation_requested = fields.Boolean(string="Confirmation demandée", default=False)
    
    @api.depends('name', 'planned_date', 'monitor_id')
    def _compute_display_name(self):
        for planning in self:
            parts = []
            if planning.planned_date:
                parts.append(planning.planned_date.strftime('%d/%m/%Y'))
            if planning.monitor_id:
                parts.append(planning.monitor_id.name)
            if planning.name:
                parts.append(planning.name)
            planning.display_name = ' - '.join(parts) if parts else 'Nouvelle planification'
    
    @api.depends('start_time', 'end_time')
    def _compute_duration_planned(self):
        for planning in self:
            planning.duration_planned = planning.end_time - planning.start_time
    
    @api.depends('actual_start_time', 'actual_end_time')
    def _compute_duration_actual(self):
        for planning in self:
            if planning.actual_start_time and planning.actual_end_time:
                planning.duration_actual = planning.actual_end_time - planning.actual_start_time
            else:
                planning.duration_actual = 0
    
    @api.depends('planned_date', 'state')
    def _compute_is_overdue(self):
        today = fields.Date.today()
        for planning in self:
            planning.is_overdue = (
                planning.planned_date < today and 
                planning.state in ['planned', 'confirmed']
            )
    
    @api.constrains('start_time', 'end_time')
    def _check_times(self):
        for planning in self:
            if planning.start_time >= planning.end_time:
                raise ValidationError("L'heure de début doit être antérieure à l'heure de fin.")
    
    @api.constrains('actual_start_time', 'actual_end_time')
    def _check_actual_times(self):
        for planning in self:
            if (planning.actual_start_time and planning.actual_end_time and 
                planning.actual_start_time >= planning.actual_end_time):
                raise ValidationError("L'heure de début réelle doit être antérieure à l'heure de fin réelle.")
    
    def action_confirm(self):
        """Confirmer la planification"""
        self.ensure_one()
        if self.state == 'planned':
            self.state = 'confirmed'
            self.confirmation_requested = True
            # Envoyer notification au moniteur
            self._send_confirmation_notification()
    
    def action_start(self):
        """Démarrer l'intervention"""
        self.ensure_one()
        if self.state in ['planned', 'confirmed']:
            self.state = 'in_progress'
            if not self.actual_start_time:
                # Définir l'heure actuelle comme heure de début
                now = datetime.now()
                self.actual_start_time = now.hour + now.minute / 60.0
    
    def action_complete(self):
        """Terminer l'intervention"""
        self.ensure_one()
        if self.state == 'in_progress':
            self.state = 'completed'
            if not self.actual_end_time:
                # Définir l'heure actuelle comme heure de fin
                now = datetime.now()
                self.actual_end_time = now.hour + now.minute / 60.0
    
    def action_cancel(self):
        """Annuler la planification"""
        self.ensure_one()
        if self.state not in ['completed', 'cancelled']:
            self.state = 'cancelled'
    
    def action_postpone(self):
        """Reporter la planification"""
        self.ensure_one()
        if self.state not in ['completed', 'cancelled']:
            self.state = 'postponed'
    
    def action_request_substitute(self):
        """Demander un remplaçant"""
        self.ensure_one()
        # Ouvrir un wizard pour sélectionner un remplaçant
        return {
            'name': 'Demander un remplaçant',
            'type': 'ir.actions.act_window',
            'res_model': 'monitor.substitute.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_planning_id': self.id,
                'default_school_id': self.school_id.id
            }
        }
    
    def _send_confirmation_notification(self):
        """Envoie une notification de confirmation au moniteur"""
        # Créer une activité de rappel
        self.env['mail.activity'].create({
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            'summary': f'Confirmation intervention - {self.display_name}',
            'note': f'''
                Bonjour {self.monitor_id.name},
                
                Vous êtes programmé(e) pour intervenir à l'école du dimanche :
                
                - École : {self.school_id.name}
                - Date : {self.planned_date.strftime("%d/%m/%Y")}
                - Horaire : {self._format_time(self.start_time)} - {self._format_time(self.end_time)}
                - Sujet : {self.topic or 'À définir'}
                
                Merci de confirmer votre disponibilité.
            ''',
            'user_id': self.env.user.id,
            'res_id': self.monitor_id.id,
            'res_model_id': self.env['ir.model']._get('res.partner').id,
            'date_deadline': self.planned_date - timedelta(days=3),
        })
    
    def _format_time(self, time_float):
        """Formate une heure décimale en HH:MM"""
        hours = int(time_float)
        minutes = int((time_float - hours) * 60)
        return f"{hours:02d}:{minutes:02d}"
    
    @api.model
    def _cron_send_reminders(self):
        """Envoie des rappels automatiques (à configurer dans les tâches planifiées)"""
        # Rappels 3 jours avant
        reminder_date = fields.Date.today() + timedelta(days=3)
        plannings_to_remind = self.search([
            ('planned_date', '=', reminder_date),
            ('state', 'in', ['planned', 'confirmed']),
            ('reminder_sent', '=', False)
        ])
        
        for planning in plannings_to_remind:
            planning._send_confirmation_notification()
            planning.reminder_sent = True
    
    @api.model
    def get_planning_statistics(self):
        """Retourne des statistiques sur les planifications"""
        stats = {}
        
        # Statistiques générales
        stats['total'] = self.search_count([])
        stats['planned'] = self.search_count([('state', '=', 'planned')])
        stats['confirmed'] = self.search_count([('state', '=', 'confirmed')])
        stats['completed'] = self.search_count([('state', '=', 'completed')])
        stats['cancelled'] = self.search_count([('state', '=', 'cancelled')])
        stats['overdue'] = self.search_count([('is_overdue', '=', True)])
        
        # Statistiques par moniteur
        monitor_stats = self.read_group(
            domain=[('state', '=', 'completed')],
            fields=['monitor_id'],
            groupby=['monitor_id']
        )
        stats['by_monitor'] = monitor_stats
        
        return stats