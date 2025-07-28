from odoo import models, fields, api
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError
import calendar

class MonitorReport(models.Model):
    """Rapports d'activité des moniteurs"""
    _name = "monitor.report"
    _description = "Rapport d'activité moniteur"
    _order = "report_date desc"

    monitor_id = fields.Many2one(
        'res.partner',
        string="Moniteur",
        domain="[('is_monitor', '=', True)]",
        required=True
    )
    
    report_date = fields.Date(
        string="Date du rapport",
        required=True,
        default=fields.Date.today
    )
    
    period_from = fields.Date(string="Période du", required=True)
    period_to = fields.Date(string="Au", required=True)
    
    # Statistiques d'activité
    total_interventions = fields.Integer(
        string="Nombre d'interventions",
        compute="_compute_activity_stats",
        store=True
    )
    
    completed_interventions = fields.Integer(
        string="Interventions terminées",
        compute="_compute_activity_stats",
        store=True
    )
    
    cancelled_interventions = fields.Integer(
        string="Interventions annulées",
        compute="_compute_activity_stats",
        store=True
    )
    
    total_hours = fields.Float(
        string="Heures totales",
        compute="_compute_activity_stats",
        store=True
    )
    
    average_participants = fields.Float(
        string="Moyenne de participants",
        compute="_compute_activity_stats",
        store=True
    )
    
    average_rating = fields.Float(
        string="Note moyenne",
        compute="_compute_activity_stats",
        store=True
    )
    
    # Rapport narratif
    activities_summary = fields.Text(string="Résumé des activités")
    achievements = fields.Text(string="Réalisations")
    challenges = fields.Text(string="Défis rencontrés")
    suggestions = fields.Text(string="Suggestions d'amélioration")
    
    # Objectifs
    objectives_met = fields.Text(string="Objectifs atteints")
    next_period_objectives = fields.Text(string="Objectifs pour la prochaine période")
    
    # Validation
    validated_by_id = fields.Many2one(
        'res.partner',
        string="Validé par"
    )
    
    validation_date = fields.Date(string="Date de validation")
    validation_comments = fields.Text(string="Commentaires de validation")
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('submitted', 'Soumis'),
        ('validated', 'Validé'),
        ('rejected', 'Rejeté')
    ], string="État", default='draft', required=True)
    
    @api.depends('monitor_id', 'period_from', 'period_to')
    def _compute_activity_stats(self):
        for report in self:
            if report.monitor_id and report.period_from and report.period_to:
                plannings = self.env['monitor.planning'].search([
                    ('monitor_id', '=', report.monitor_id.id),
                    ('planned_date', '>=', report.period_from),
                    ('planned_date', '<=', report.period_to)
                ])
                
                report.total_interventions = len(plannings)
                report.completed_interventions = len(plannings.filtered(lambda p: p.state == 'completed'))
                report.cancelled_interventions = len(plannings.filtered(lambda p: p.state == 'cancelled'))
                
                completed_plannings = plannings.filtered(lambda p: p.state == 'completed')
                if completed_plannings:
                    report.total_hours = sum(completed_plannings.mapped('duration_actual'))
                    report.average_participants = sum(completed_plannings.mapped('actual_participants')) / len(completed_plannings)
                    
                    ratings = [int(p.rating) for p in completed_plannings if p.rating]
                    report.average_rating = sum(ratings) / len(ratings) if ratings else 0
                else:
                    report.total_hours = 0
                    report.average_participants = 0
                    report.average_rating = 0
            else:
                report.total_interventions = 0
                report.completed_interventions = 0
                report.cancelled_interventions = 0
                report.total_hours = 0
                report.average_participants = 0
                report.average_rating = 0
    
    def action_submit(self):
        """Soumettre le rapport"""
        self.ensure_one()
        if self.state == 'draft':
            self.state = 'submitted'
    
    def action_validate(self):
        """Valider le rapport"""
        self.ensure_one()
        if self.state == 'submitted':
            self.state = 'validated'
            self.validated_by_id = self.env.user.partner_id.id
            self.validation_date = fields.Date.today()
    
    def action_reject(self):
        """Rejeter le rapport"""
        self.ensure_one()
        if self.state == 'submitted':
            self.state = 'rejected'