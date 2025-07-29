from odoo import http
from odoo.http import request
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json
import logging

_logger = logging.getLogger(__name__)


class MonitorPlanningWebController(http.Controller):

    @http.route("/monitor/planning", type="http", auth="public", website=True)
    def monitor_planning_list(self, **kw):
        """Page principale de planification des moniteurs"""

        # Récupérer les paramètres de filtrage
        school_id = kw.get("school_id")
        monitor_id = kw.get("monitor_id")
        date_from = kw.get("date_from")
        date_to = kw.get("date_to")

        # Domaine de base
        domain = [("state", "in", ["planned", "confirmed", "completed"])]

        # Filtres avec validation
        if school_id:
            try:
                domain.append(("school_id", "=", int(school_id)))
            except (ValueError, TypeError):
                _logger.warning(f"ID école invalide: {school_id}")

        if monitor_id:
            try:
                domain.append(("monitor_id", "=", int(monitor_id)))
            except (ValueError, TypeError):
                _logger.warning(f"ID moniteur invalide: {monitor_id}")

        # Période par défaut : 3 prochains mois
        if not date_from:
            date_from = datetime.now().strftime("%Y-%m-%d")
        else:
            # Valider le format de date
            try:
                datetime.strptime(date_from, "%Y-%m-%d")
            except ValueError:
                _logger.warning(f"Format de date_from invalide: {date_from}")
                date_from = datetime.now().strftime("%Y-%m-%d")

        if not date_to:
            date_to = (datetime.now() + relativedelta(months=3)).strftime("%Y-%m-%d")
        else:
            try:
                datetime.strptime(date_to, "%Y-%m-%d")
            except ValueError:
                _logger.warning(f"Format de date_to invalide: {date_to}")
                date_to = (datetime.now() + relativedelta(months=3)).strftime(
                    "%Y-%m-%d"
                )

        domain.extend(
            [("planned_date", ">=", date_from), ("planned_date", "<=", date_to)]
        )

        # Récupérer les planifications
        plannings = (
            request.env["monitor.planning"]
            .sudo()
            .search(domain, order="planned_date asc, start_time asc")
        )

        # Listes pour les filtres
        schools = (
            request.env["res.partner"]
            .sudo()
            .search([("organization_type", "=", "school")])
        )
        monitors = request.env["res.partner"].sudo().search([("is_monitor", "=", True)])

        # Grouper par semaine pour un meilleur affichage
        weekly_plannings = self._group_plannings_by_week(plannings)

        values = {
            "plannings": plannings,
            "weekly_plannings": weekly_plannings,
            "schools": schools,
            "monitors": monitors,
            "selected_school_id": (
                int(school_id) if school_id and school_id.isdigit() else None
            ),
            "selected_monitor_id": (
                int(monitor_id) if monitor_id and monitor_id.isdigit() else None
            ),
            "date_from": date_from,
            "date_to": date_to,
        }

        return request.render("monitor_planning.monitor_planning_template", values)

    @http.route("/monitor/planning/calendar", type="http", auth="public", website=True)
    def monitor_planning_calendar(self, **kw):
        """Vue calendrier des planifications améliorée et corrigée"""

        # Récupérer les paramètres de filtrage
        school_id = kw.get("school_id")
        monitor_id = kw.get("monitor_id")
        status_filter = kw.get("status")

        # Récupérer le mois/année avec validation
        try:
            year = int(kw.get("year", datetime.now().year))
            month = int(kw.get("month", datetime.now().month))
        except (ValueError, TypeError):
            year = datetime.now().year
            month = datetime.now().month

        # Validation des valeurs
        if not (1 <= month <= 12):
            month = datetime.now().month
        if year < 1900 or year > 2100:
            year = datetime.now().year

        # Premier et dernier jour du mois
        try:
            first_day = datetime(year, month, 1).date()
            if month == 12:
                last_day = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                last_day = datetime(year, month + 1, 1).date() - timedelta(days=1)
        except ValueError:
            # Fallback en cas d'erreur
            first_day = datetime.now().replace(day=1).date()
            last_day = (
                datetime.now().replace(day=1)
                + relativedelta(months=1)
                - timedelta(days=1)
            ).date()

        # Construction du domaine de recherche avec filtres
        domain = [
            ("planned_date", ">=", first_day),
            ("planned_date", "<=", last_day),
        ]

        # Filtre par statut
        if status_filter and status_filter in ["planned", "confirmed", "completed", "cancelled"]:
            domain.append(("state", "=", status_filter))
        else:
            domain.append(("state", "in", ["planned", "confirmed", "completed"]))

        # Filtre par école
        if school_id:
            try:
                domain.append(("school_id", "=", int(school_id)))
            except (ValueError, TypeError):
                _logger.warning(f"ID école invalide: {school_id}")

        # Filtre par moniteur
        if monitor_id:
            try:
                domain.append(("monitor_id", "=", int(monitor_id)))
            except (ValueError, TypeError):
                _logger.warning(f"ID moniteur invalide: {monitor_id}")

        # Récupérer les planifications du mois
        plannings = (
            request.env["monitor.planning"]
            .sudo()
            .search(domain, order="planned_date asc, start_time asc")
        )

        # Grouper par date
        daily_plannings = {}
        for planning in plannings:
            if planning.planned_date:  # Vérifier que la date existe
                date_key = planning.planned_date.strftime("%Y-%m-%d")
                if date_key not in daily_plannings:
                    daily_plannings[date_key] = []
                daily_plannings[date_key].append(planning)

        # Calculer les statistiques du mois
        statistics = self._calculate_monthly_statistics(plannings)

        # Récupérer les listes pour les filtres
        schools = (
            request.env["res.partner"]
            .sudo()
            .search([("organization_type", "=", "school")], order="name")
        )
        monitors = (
            request.env["res.partner"]
            .sudo()
            .search([("is_monitor", "=", True)], order="name")
        )

        # Navigation mois précédent/suivant
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1

        # Nom du mois en français
        month_names = [
            "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
            "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
        ]
        month_name = f"{month_names[month-1]} {year}"

        values = {
            "current_year": year,
            "current_month": month,
            "month_name": month_name,
            "daily_plannings": daily_plannings,
            "first_day": first_day,
            "last_day": last_day,
            "prev_month": prev_month,
            "prev_year": prev_year,
            "next_month": next_month,
            "next_year": next_year,
            "timedelta": timedelta,  # Pour le template
            "datetime": datetime,    # Pour le template
            
            # Données pour les améliorations
            "schools": schools,
            "monitors": monitors,
            "selected_school_id": int(school_id) if school_id and school_id.isdigit() else None,
            "selected_monitor_id": int(monitor_id) if monitor_id and monitor_id.isdigit() else None,
            "selected_status": status_filter,
            
            # Statistiques du mois
            "total_plannings": statistics["total"],
            "total_planned": statistics["planned"],
            "total_confirmed": statistics["confirmed"],
            "total_completed": statistics["completed"],
            "total_cancelled": statistics["cancelled"],
        }

        return request.render(
            "monitor_planning.monitor_planning_calendar_template", values
        )

    @http.route("/monitor/planning/day/<string:date>", type="http", auth="public", website=True)
    def monitor_planning_day_detail(self, date, **kw):
        """Vue détaillée d'un jour spécifique"""
        
        try:
            # Valider et parser la date
            date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            return request.not_found()

        # Récupérer les planifications du jour
        plannings = (
            request.env["monitor.planning"]
            .sudo()
            .search([
                ("planned_date", "=", date_obj),
                ("state", "in", ["planned", "confirmed", "completed"])
            ], order="start_time asc")
        )

        # Calculer les statistiques du jour
        day_stats = {
            "total": len(plannings),
            "planned": len([p for p in plannings if p.state == "planned"]),
            "confirmed": len([p for p in plannings if p.state == "confirmed"]),
            "completed": len([p for p in plannings if p.state == "completed"]),
        }

        # Noms des jours en français
        day_names = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        month_names = [
            "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
            "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
        ]
        
        date_formatted = f"{day_names[date_obj.weekday()]} {date_obj.day} {month_names[date_obj.month-1]} {date_obj.year}"

        values = {
            "date": date_obj,
            "date_formatted": date_formatted,
            "plannings": plannings,
            "day_stats": day_stats,
        }

        # Vérifier si le template existe, sinon rediriger vers le calendrier
        try:
            return request.render("monitor_planning.monitor_planning_day_detail_template", values)
        except ValueError:
            # Template non trouvé, rediriger vers le calendrier avec un message
            year = date_obj.year
            month = date_obj.month
            return request.redirect(f"/monitor/planning/calendar?year={year}&month={month}")


    @http.route("/monitor/planning/<int:planning_id>", type="http", auth="public", website=True)
    def monitor_planning_detail(self, planning_id, **kw):
        """Détail d'une planification"""

        planning = request.env["monitor.planning"].sudo().browse(planning_id)
        if not planning.exists():
            return request.not_found()

        values = {
            "planning": planning,
        }

        return request.render(
            "monitor_planning.monitor_planning_detail_template", values
        )


    @http.route("/monitor/planning/pdf", type="http", auth="public", website=True)
    def monitor_planning_pdf(self, **kw):
        """Génération PDF de la planification"""

        try:
            # Récupérer les filtres avec validation
            school_id = kw.get("school_id")
            monitor_id = kw.get("monitor_id")
            date_from = kw.get("date_from")
            date_to = kw.get("date_to")

            # Construction du domaine de recherche
            domain = [("state", "in", ["planned", "confirmed", "completed"])]

            # Variables pour les noms à afficher
            selected_school_name = None
            selected_monitor_name = None

            # Validation et ajout des filtres
            if school_id:
                try:
                    school_id = int(school_id)
                    domain.append(("school_id", "=", school_id))
                    # Récupérer le nom de l'école
                    school = request.env["res.partner"].sudo().browse(school_id)
                    if school.exists():
                        selected_school_name = school.name
                except ValueError:
                    _logger.warning(f"ID école invalide: {school_id}")

            if monitor_id:
                try:
                    monitor_id = int(monitor_id)
                    domain.append(("monitor_id", "=", monitor_id))
                    # Récupérer le nom du moniteur
                    monitor = request.env["res.partner"].sudo().browse(monitor_id)
                    if monitor.exists():
                        selected_monitor_name = monitor.name
                except ValueError:
                    _logger.warning(f"ID moniteur invalide: {monitor_id}")

            # Gestion des dates avec validation
            if not date_from:
                date_from = datetime.now().strftime("%Y-%m-%d")
            else:
                try:
                    datetime.strptime(date_from, "%Y-%m-%d")
                except ValueError:
                    _logger.warning(f"Format de date_from invalide: {date_from}")
                    date_from = datetime.now().strftime("%Y-%m-%d")

            if not date_to:
                date_to = (datetime.now() + relativedelta(months=3)).strftime(
                    "%Y-%m-%d"
                )
            else:
                try:
                    datetime.strptime(date_to, "%Y-%m-%d")
                except ValueError:
                    _logger.warning(f"Format de date_to invalide: {date_to}")
                    date_to = (datetime.now() + relativedelta(months=3)).strftime(
                        "%Y-%m-%d"
                    )

            # Ajouter les filtres de date
            domain.extend(
                [("planned_date", ">=", date_from), ("planned_date", "<=", date_to)]
            )

            # Rechercher les planifications
            plannings = (
                request.env["monitor.planning"]
                .sudo()
                .search(domain, order="planned_date asc, start_time asc")
            )

            # Vérifier s'il y a des données
            if not plannings:
                # Retourner une page d'erreur au lieu d'un message texte
                values = {
                    "error_message": "Aucune planification trouvée pour les critères spécifiés.",
                    "date_from": date_from,
                    "date_to": date_to,
                    "selected_school_name": selected_school_name,
                    "selected_monitor_name": selected_monitor_name,
                }
                return request.render(
                    "monitor_planning.monitor_planning_pdf_error_template", values
                )

            # Calculer les statistiques
            statistics = self._calculate_monthly_statistics(plannings)
            
            # Construire le titre du rapport
            report_title = "Planification des Moniteurs d'École du Dimanche"

            if selected_school_name:
                report_title += f" - {selected_school_name}"

            if selected_monitor_name:
                report_title += f" - {selected_monitor_name}"

            # Préparer les données pour le template
            values = {
                "plannings": plannings,
                "report_title": report_title,
                "date_from": date_from,
                "date_to": date_to,
                "generation_date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "weekly_plannings": self._group_plannings_by_week(plannings),
                "selected_school_name": selected_school_name,
                "selected_monitor_name": selected_monitor_name,
                # Ajouter les statistiques calculées
                "stats": statistics,
                # Ajouter les objets nécessaires pour le template
                "datetime": datetime,
            }

            # Vérifier l'existence du rapport
            report_ref = request.env.ref(
                "monitor_planning.monitor_planning_pdf_report", raise_if_not_found=False
            )
            if not report_ref:
                _logger.error(
                    "Template de rapport PDF introuvable: monitor_planning.monitor_planning_pdf_report"
                )
                return request.make_response(
                    "Erreur: Template de rapport non trouvé.",
                    status=500,
                    headers=[("Content-Type", "text/plain")],
                )

            # Générer le PDF avec gestion d'erreur améliorée
            try:
                pdf_content, pdf_type = report_ref.sudo()._render_qweb_pdf(
                    'monitor_planning.monitor_planning_pdf_template', 
                    plannings.ids, data=values
                )

                if not pdf_content:
                    raise Exception("Le contenu PDF généré est vide")

            except Exception as pdf_error:
                _logger.error(f"Erreur lors du rendu PDF: {str(pdf_error)}")
                # En cas d'erreur PDF, retourner la version HTML
                return request.render(
                    "monitor_planning.monitor_planning_pdf_template", values
                )

            # Générer un nom de fichier sécurisé
            safe_date_from = date_from.replace("-", "")
            safe_date_to = date_to.replace("-", "")
            filename = f"planification_moniteurs_{safe_date_from}_{safe_date_to}.pdf"
        
            pdfhttpheaders = [
                ("Content-Type", "application/pdf"),
                ("Content-Disposition", f'attachment; filename="{filename}"'),
                ("Content-Length", len(pdf_content)),
                ("Cache-Control", "no-cache"),
            ]
            return request.make_response(pdf_content, headers=pdfhttpheaders)

        except Exception as e:
            _logger.error(f"Erreur lors de la génération du PDF: {str(e)}")
            # Retourner une page d'erreur au lieu d'un message texte
            error_values = {
                "error_message": f"Erreur lors de la génération du PDF: {str(e)}",
                "date_from": kw.get("date_from", ""),
                "date_to": kw.get("date_to", ""),
            }
            return request.render(
                "monitor_planning.monitor_planning_pdf_error_template", error_values
            )

    @http.route("/monitor/planning/api/calendar-data", type="json", auth="public")
    def calendar_api_data(self, **kw):
        """API pour récupérer les données du calendrier avec filtres"""
        
        try:
            year = int(kw.get("year", datetime.now().year))
            month = int(kw.get("month", datetime.now().month))
            
            # Validation
            if not (1 <= month <= 12) or year < 1900 or year > 2100:
                return {"error": "Paramètres de date invalides"}
            
            # Dates du mois
            first_day = datetime(year, month, 1).date()
            if month == 12:
                last_day = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                last_day = datetime(year, month + 1, 1).date() - timedelta(days=1)
            
            # Construction du domaine avec filtres
            domain = [
                ("planned_date", ">=", first_day),
                ("planned_date", "<=", last_day),
                ("state", "in", ["planned", "confirmed", "completed"])
            ]
            
            # Appliquer les filtres
            if kw.get("school_id"):
                domain.append(("school_id", "=", int(kw["school_id"])))
            if kw.get("monitor_id"):
                domain.append(("monitor_id", "=", int(kw["monitor_id"])))
            if kw.get("status"):
                domain = [d for d in domain if not (isinstance(d, tuple) and d[0] == "state")]
                domain.append(("state", "=", kw["status"]))
            
            plannings = request.env["monitor.planning"].sudo().search(domain)
            
            # Formater les données
            daily_data = {}
            for planning in plannings:
                date_key = planning.planned_date.strftime("%Y-%m-%d")
                if date_key not in daily_data:
                    daily_data[date_key] = []
                
                daily_data[date_key].append({
                    "id": planning.id,
                    "monitor": planning.monitor_id.name if planning.monitor_id else "N/D",
                    "school": planning.school_id.name if planning.school_id else "N/D",
                    "time": self._format_time(planning.start_time),
                    "state": planning.state,
                    "topic": planning.topic or ""
                })
            
            # Statistiques
            stats = self._calculate_monthly_statistics(plannings)
            
            return {
                "success": True,
                "daily_plannings": daily_data,
                "statistics": stats
            }
            
        except Exception as e:
            _logger.error(f"Erreur API calendrier: {str(e)}")
            return {"error": str(e)}


    def _calculate_monthly_statistics(self, plannings):
        """Calculer les statistiques mensuelles"""
        try:
            stats = {
                "total": len(plannings),
                "planned": 0,
                "confirmed": 0,
                "completed": 0,
                "cancelled": 0
            }
            
            for planning in plannings:
                state = getattr(planning, 'state', None)
                if state in stats:
                    stats[state] += 1
                elif state == 'cancelled':
                    stats['cancelled'] += 1
            
            return stats
            
        except Exception as e:
            _logger.error(f"Erreur calcul statistiques mensuelles: {str(e)}")
            return {"total": 0, "planned": 0, "confirmed": 0, "completed": 0, "cancelled": 0}


    def _calculate_statistics(self, plannings):
        """Calculer les statistiques des planifications"""
        try:
            stats = {
                'total': len(plannings),
                'planned': 0,
                'confirmed': 0,
                'completed': 0,
                'cancelled': 0,
                'monitor_stats': {},
                'school_stats': {}
            }
            
            for planning in plannings:
                if not planning:
                    continue
                    
                # Compter par état
                state = getattr(planning, 'state', None)
                if state == 'planned':
                    stats['planned'] += 1
                elif state == 'confirmed':
                    stats['confirmed'] += 1
                elif state == 'completed':
                    stats['completed'] += 1
                elif state == 'cancelled':
                    stats['cancelled'] += 1
                
                # Statistiques par moniteur
                monitor = getattr(planning, 'monitor_id', None)
                monitor_name = getattr(monitor, 'name', None) if monitor else 'Moniteur N/D'
                if monitor_name not in stats['monitor_stats']:
                    stats['monitor_stats'][monitor_name] = 0
                stats['monitor_stats'][monitor_name] += 1
                
                # Statistiques par école
                school = getattr(planning, 'school_id', None)
                school_name = getattr(school, 'name', None) if school else 'École N/D'
                if school_name not in stats['school_stats']:
                    stats['school_stats'][school_name] = 0
                stats['school_stats'][school_name] += 1
            
            return stats
            
        except Exception as e:
            _logger.error(f"Erreur lors du calcul des statistiques: {str(e)}")
            return {
                'total': 0,
                'planned': 0,
                'confirmed': 0,
                'completed': 0,
                'cancelled': 0,
                'monitor_stats': {},
                'school_stats': {}
            }

    def _group_plannings_by_week(self, plannings):
        """Grouper les planifications par semaine avec gestion d'erreur améliorée"""
        try:
            weekly_plannings = {}

            for planning in plannings:
                if not planning.planned_date:
                    continue

                # Convertir la date en objet datetime si nécessaire
                try:
                    if isinstance(planning.planned_date, str):
                        date_obj = datetime.strptime(planning.planned_date, "%Y-%m-%d")
                    else:
                        # Si c'est un objet date
                        if hasattr(planning.planned_date, "year"):
                            if hasattr(planning.planned_date, "hour"):  # datetime
                                date_obj = planning.planned_date
                            else:  # date
                                date_obj = datetime.combine(
                                    planning.planned_date, datetime.min.time()
                                )
                        else:
                            continue

                    # Calculer le début de la semaine (lundi)
                    week_start = date_obj - timedelta(days=date_obj.weekday())
                    week_key = week_start.strftime("%Y-%m-%d")

                    if week_key not in weekly_plannings:
                        weekly_plannings[week_key] = {
                            "week_start": week_start,
                            "week_end": week_start + timedelta(days=6),
                            "plannings": [],
                        }

                    weekly_plannings[week_key]["plannings"].append(planning)

                except (ValueError, TypeError) as date_error:
                    _logger.warning(
                        f"Erreur de conversion de date pour planning {planning.id}: {str(date_error)}"
                    )
                    continue

            # Trier les semaines par date
            return dict(sorted(weekly_plannings.items()))

        except Exception as e:
            _logger.error(f"Erreur lors du groupement par semaine: {str(e)}")
            return {}

    def _format_time(self, time_float):
        """Formate une heure décimale en HH:MM"""
        try:
            if time_float is None:
                return "00:00"
            hours = int(time_float)
            minutes = int((time_float - hours) * 60)
            return f"{hours:02d}:{minutes:02d}"
        except (ValueError, TypeError):
            return "00:00"

    

    @http.route("/monitor/planning/api/data", type="json", auth="public")
    def monitor_planning_api_data(self, **kw):
        """API JSON pour récupérer les données de planification"""

        try:
            domain = [("state", "in", ["planned", "confirmed", "completed"])]

            # Filtres depuis les paramètres JSON avec validation
            if kw.get("school_id"):
                try:
                    domain.append(("school_id", "=", int(kw["school_id"])))
                except (ValueError, TypeError):
                    pass

            if kw.get("monitor_id"):
                try:
                    domain.append(("monitor_id", "=", int(kw["monitor_id"])))
                except (ValueError, TypeError):
                    pass

            if kw.get("date_from"):
                try:
                    datetime.strptime(kw["date_from"], "%Y-%m-%d")
                    domain.append(("planned_date", ">=", kw["date_from"]))
                except ValueError:
                    pass

            if kw.get("date_to"):
                try:
                    datetime.strptime(kw["date_to"], "%Y-%m-%d")
                    domain.append(("planned_date", "<=", kw["date_to"]))
                except ValueError:
                    pass

            plannings = request.env["monitor.planning"].sudo().search(domain)

            data = []
            for planning in plannings:
                data.append(
                    {
                        "id": planning.id,
                        "name": planning.name or "",
                        "school": planning.school_id.name if planning.school_id else "",
                        "monitor": (
                            planning.monitor_id.name if planning.monitor_id else ""
                        ),
                        "date": (
                            planning.planned_date.strftime("%Y-%m-%d")
                            if planning.planned_date
                            else ""
                        ),
                        "start_time": planning.start_time or 0,
                        "end_time": planning.end_time or 0,
                        "state": planning.state or "",
                        "topic": planning.topic or "",
                        "expected_participants": planning.expected_participants or 0,
                    }
                )

            return {"plannings": data}

        except Exception as e:
            _logger.error(f"Erreur dans l'API JSON: {str(e)}")
            return {"error": str(e), "plannings": []}