from odoo import models, fields, api
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError
import calendar

# Extension du modèle res.partner pour ajouter les statistiques de planification
class ResPartner(models.Model):
    _inherit = "res.partner"

    # Statistiques pour les moniteurs
    planning_count = fields.Integer(
        string="Nombre de planifications", compute="_compute_monitor_planning_stats"
    )

    completed_planning_count = fields.Integer(
        string="Interventions terminées", compute="_compute_monitor_planning_stats"
    )

    upcoming_planning_count = fields.Integer(
        string="Interventions à venir", compute="_compute_monitor_planning_stats"
    )

    substitute_count = fields.Integer(
        string="Remplacements effectués", compute="_compute_monitor_planning_stats"
    )

    # Nouvelles statistiques pour les moniteurs
    availability_count = fields.Integer(
        string="Disponibilités déclarées", compute="_compute_extended_monitor_stats"
    )

    evaluation_count = fields.Integer(
        string="Évaluations reçues", compute="_compute_extended_monitor_stats"
    )

    training_count = fields.Integer(
        string="Formations suivies", compute="_compute_extended_monitor_stats"
    )

    certificate_count = fields.Integer(
        string="Certificats obtenus", compute="_compute_extended_monitor_stats"
    )

    report_count = fields.Integer(
        string="Rapports soumis", compute="_compute_extended_monitor_stats"
    )

    last_evaluation_date = fields.Date(
        string="Dernière évaluation", compute="_compute_extended_monitor_stats"
    )

    last_training_date = fields.Date(
        string="Dernière formation", compute="_compute_extended_monitor_stats"
    )

    average_evaluation_rating = fields.Float(
        string="Note moyenne d'évaluation", compute="_compute_extended_monitor_stats"
    )

    @api.depends()
    def _compute_monitor_planning_stats(self):
        for partner in self:
            if partner.is_monitor:
                # Planifications principales
                partner.planning_count = self.env["monitor.planning"].search_count(
                    [("monitor_id", "=", partner.id)]
                )

                partner.completed_planning_count = self.env[
                    "monitor.planning"
                ].search_count(
                    [("monitor_id", "=", partner.id), ("state", "=", "completed")]
                )

                partner.upcoming_planning_count = self.env[
                    "monitor.planning"
                ].search_count(
                    [
                        ("monitor_id", "=", partner.id),
                        ("state", "in", ["planned", "confirmed"]),
                        ("planned_date", ">=", fields.Date.today()),
                    ]
                )

                # Remplacements
                partner.substitute_count = self.env["monitor.planning"].search_count(
                    [
                        ("substitute_monitor_id", "=", partner.id),
                        ("state", "=", "completed"),
                    ]
                )
            else:
                partner.planning_count = 0
                partner.completed_planning_count = 0
                partner.upcoming_planning_count = 0
                partner.substitute_count = 0

    def action_view_monitor_plannings(self):
        """Action pour voir les planifications du moniteur"""
        if not self.is_monitor:
            return False

        return {
            "name": f"Planifications de {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "monitor.planning",
            "view_mode": "calendar,tree,form",
            "domain": [
                "|",
                ("monitor_id", "=", self.id),
                ("substitute_monitor_id", "=", self.id),
            ],
            "context": {"default_monitor_id": self.id},
        }

    def action_view_upcoming_plannings(self):
        """Action pour voir les prochaines interventions"""
        if not self.is_monitor:
            return False

        return {
            "name": f"Prochaines interventions - {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "monitor.planning",
            "view_mode": "calendar,tree,form",
            "domain": [
                ("monitor_id", "=", self.id),
                ("state", "in", ["planned", "confirmed"]),
                ("planned_date", ">=", fields.Date.today()),
            ],
            "context": {"default_monitor_id": self.id},
        }

    @api.depends()
    def _compute_extended_monitor_stats(self):
        for partner in self:
            if partner.is_monitor:
                # Disponibilités
                partner.availability_count = self.env[
                    "monitor.availability"
                ].search_count([("monitor_id", "=", partner.id)])

                # Évaluations
                evaluations = self.env["monitor.evaluation"].search(
                    [("monitor_id", "=", partner.id)]
                )
                partner.evaluation_count = len(evaluations)

                if evaluations:
                    partner.last_evaluation_date = max(
                        evaluations.mapped("evaluation_date")
                    )
                    partner.average_evaluation_rating = sum(
                        evaluations.mapped("overall_rating")
                    ) / len(evaluations)
                else:
                    partner.last_evaluation_date = False
                    partner.average_evaluation_rating = 0.0

                # Formations
                trainings = self.env["monitor.training"].search(
                    [("participant_ids", "in", partner.id)]
                )
                partner.training_count = len(trainings)

                if trainings:
                    partner.last_training_date = max(trainings.mapped("date"))
                else:
                    partner.last_training_date = False

                # Certificats
                partner.certificate_count = self.env[
                    "monitor.certificate"
                ].search_count([("monitor_id", "=", partner.id)])

                # Rapports
                partner.report_count = self.env["monitor.report"].search_count(
                    [("monitor_id", "=", partner.id)]
                )
            else:
                partner.availability_count = 0
                partner.evaluation_count = 0
                partner.training_count = 0
                partner.certificate_count = 0
                partner.report_count = 0
                partner.last_evaluation_date = False
                partner.last_training_date = False
                partner.average_evaluation_rating = 0.0

    def action_view_monitor_availabilities(self):
        """Action pour voir les disponibilités du moniteur"""
        return {
            "name": f"Disponibilités - {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "monitor.availability",
            "view_mode": "tree,form",
            "domain": [("monitor_id", "=", self.id)],
            "context": {"default_monitor_id": self.id},
        }

    def action_view_monitor_evaluations(self):
        """Action pour voir les évaluations du moniteur"""
        return {
            "name": f"Évaluations - {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "monitor.evaluation",
            "view_mode": "tree,form",
            "domain": [("monitor_id", "=", self.id)],
            "context": {"default_monitor_id": self.id},
        }

    def action_view_monitor_trainings(self):
        """Action pour voir les formations du moniteur"""
        return {
            "name": f"Formations - {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "monitor.training",
            "view_mode": "tree,form",
            "domain": [("participant_ids", "in", self.id)],
        }

    def action_view_monitor_certificates(self):
        """Action pour voir les certificats du moniteur"""
        return {
            "name": f"Certificats - {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "monitor.certificate",
            "view_mode": "tree,form",
            "domain": [("monitor_id", "=", self.id)],
            "context": {"default_monitor_id": self.id},
        }

    def action_view_monitor_reports(self):
        """Action pour voir les rapports du moniteur"""
        return {
            "name": f"Rapports - {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "monitor.report",
            "view_mode": "tree,form",
            "domain": [("monitor_id", "=", self.id)],
            "context": {"default_monitor_id": self.id},
        }
