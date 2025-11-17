"""
Workflow Automation Engine
Executes multi-step workflows for automated remediation
"""
import os
import sys
import json
import uuid
import sqlite3
import threading
from datetime import datetime
from typing import List, Dict, Any, Callable
from enum import Enum

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from lab.common.logging_config import setup_logging

logger = setup_logging('workflow_engine')


class WorkflowStatus(Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStep:
    """Individual workflow step"""
    
    def __init__(self, step_id: str, action: str, params: Dict = None,
                 requires_approval: bool = False, timeout_seconds: int = 300):
        self.step_id = step_id
        self.action = action
        self.params = params or {}
        self.requires_approval = requires_approval
        self.timeout_seconds = timeout_seconds
        self.status = WorkflowStatus.PENDING
        self.result = None
        self.error = None
        self.started_at = None
        self.completed_at = None
    
    def to_dict(self) -> Dict:
        return {
            'step_id': self.step_id,
            'action': self.action,
            'params': self.params,
            'requires_approval': self.requires_approval,
            'status': self.status.value,
            'result': self.result,
            'error': self.error,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class Workflow:
    """Workflow definition"""
    
    def __init__(self, workflow_id: str, name: str, description: str,
                 steps: List[WorkflowStep], trigger_condition: str = None):
        self.workflow_id = workflow_id
        self.name = name
        self.description = description
        self.steps = steps
        self.trigger_condition = trigger_condition
        self.status = WorkflowStatus.PENDING
        self.current_step_index = 0
        self.created_at = datetime.utcnow()
        self.started_at = None
        self.completed_at = None
        self.metadata = {}
    
    def to_dict(self) -> Dict:
        return {
            'workflow_id': self.workflow_id,
            'name': self.name,
            'description': self.description,
            'trigger_condition': self.trigger_condition,
            'status': self.status.value,
            'current_step': self.current_step_index,
            'total_steps': len(self.steps),
            'steps': [step.to_dict() for step in self.steps],
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'metadata': self.metadata
        }


class WorkflowEngine:
    """Workflow automation engine with persistence"""

    def __init__(self, storage_path: str = '/data/workflows.db'):
        self.storage_path = storage_path
        self.workflows: Dict[str, Workflow] = {}
        self.workflow_templates: Dict[str, Workflow] = {}
        self.action_handlers: Dict[str, Callable] = {}
        self._local = threading.local()
        self._lock = threading.Lock()

        self._init_db()
        self._register_builtin_actions()
        self._restore_workflows()

        logger.info(f"Workflow engine initialized with persistence at {storage_path}")

    @property
    def connection(self):
        """Thread-local connection with WAL mode"""
        if not hasattr(self._local, 'connection'):
            conn = sqlite3.connect(
                self.storage_path,
                check_same_thread=False,
                timeout=10.0,
                isolation_level=None
            )
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA synchronous=NORMAL')
            self._local.connection = conn
            logger.debug(f"Created workflow DB connection for thread {threading.get_ident()}")
        return self._local.connection

    def _init_db(self):
        """Initialize workflow persistence database"""
        conn = self.connection
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workflows (
                workflow_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                trigger_condition TEXT,
                status TEXT NOT NULL,
                current_step_index INTEGER DEFAULT 0,
                steps_json TEXT NOT NULL,
                metadata_json TEXT,
                created_at TIMESTAMP NOT NULL,
                started_at TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workflow_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_workflow_status ON workflows(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_workflow ON workflow_history(workflow_id)')

        logger.info("Workflow persistence database initialized")

    def _persist_workflow(self, workflow: Workflow):
        """Persist workflow state to database"""
        with self._lock:
            conn = self.connection
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO workflows
                (workflow_id, name, description, trigger_condition, status,
                 current_step_index, steps_json, metadata_json, created_at,
                 started_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                workflow.workflow_id,
                workflow.name,
                workflow.description,
                workflow.trigger_condition,
                workflow.status.value,
                workflow.current_step_index,
                json.dumps([step.to_dict() for step in workflow.steps]),
                json.dumps(workflow.metadata),
                workflow.created_at.isoformat(),
                workflow.started_at.isoformat() if workflow.started_at else None,
                workflow.completed_at.isoformat() if workflow.completed_at else None
            ))

    def _log_workflow_event(self, workflow_id: str, event_type: str, event_data: Dict = None):
        """Log workflow event to history"""
        conn = self.connection
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO workflow_history (workflow_id, event_type, event_data)
            VALUES (?, ?, ?)
        ''', (workflow_id, event_type, json.dumps(event_data or {})))

    def _restore_workflows(self):
        """Restore workflows from database on startup"""
        conn = self.connection
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM workflows WHERE status IN (?, ?, ?)',
                       (WorkflowStatus.RUNNING.value,
                        WorkflowStatus.WAITING_APPROVAL.value,
                        WorkflowStatus.APPROVED.value))

        rows = cursor.fetchall()

        for row in rows:
            workflow_id = row[0]
            name = row[1]
            description = row[2]
            trigger_condition = row[3]
            status = WorkflowStatus(row[4])
            current_step_index = row[5]
            steps_json = json.loads(row[6])
            metadata_json = json.loads(row[7]) if row[7] else {}
            created_at = datetime.fromisoformat(row[8])
            started_at = datetime.fromisoformat(row[9]) if row[9] else None
            completed_at = datetime.fromisoformat(row[10]) if row[10] else None

            # Reconstruct workflow steps
            steps = []
            for step_data in steps_json:
                step = WorkflowStep(
                    step_id=step_data['step_id'],
                    action=step_data['action'],
                    params=step_data['params'],
                    requires_approval=step_data['requires_approval']
                )
                step.status = WorkflowStatus(step_data['status'])
                step.result = step_data['result']
                step.error = step_data['error']
                if step_data['started_at']:
                    step.started_at = datetime.fromisoformat(step_data['started_at'])
                if step_data['completed_at']:
                    step.completed_at = datetime.fromisoformat(step_data['completed_at'])
                steps.append(step)

            # Reconstruct workflow
            workflow = Workflow(
                workflow_id=workflow_id,
                name=name,
                description=description,
                steps=steps,
                trigger_condition=trigger_condition
            )
            workflow.status = status
            workflow.current_step_index = current_step_index
            workflow.created_at = created_at
            workflow.started_at = started_at
            workflow.completed_at = completed_at
            workflow.metadata = metadata_json

            self.workflows[workflow_id] = workflow
            logger.info(f"Restored workflow: {workflow_id} (status: {status.value})")

        logger.info(f"Restored {len(rows)} workflows from database")
    
    def _register_builtin_actions(self):
        """Register built-in action handlers"""
        self.action_handlers['log'] = self._action_log
        self.action_handlers['http_request'] = self._action_http_request
        self.action_handlers['execute_command'] = self._action_execute_command
        self.action_handlers['send_notification'] = self._action_send_notification
        self.action_handlers['restart_service'] = self._action_restart_service
        self.action_handlers['scale_service'] = self._action_scale_service
    
    def register_template(self, template: Workflow):
        """Register a workflow template"""
        self.workflow_templates[template.workflow_id] = template
        logger.info(f"Registered workflow template: {template.name}")
    
    def create_workflow_from_template(self, template_id: str, metadata: Dict = None) -> Workflow:
        """Create workflow instance from template"""
        if template_id not in self.workflow_templates:
            raise ValueError(f"Template not found: {template_id}")
        
        template = self.workflow_templates[template_id]
        
        # Create new workflow instance
        workflow = Workflow(
            workflow_id=f"wf-{uuid.uuid4().hex[:12]}",
            name=template.name,
            description=template.description,
            steps=[
                WorkflowStep(
                    step_id=f"{template_id}-step-{i}",
                    action=step.action,
                    params=step.params.copy(),
                    requires_approval=step.requires_approval,
                    timeout_seconds=step.timeout_seconds
                )
                for i, step in enumerate(template.steps)
            ],
            trigger_condition=template.trigger_condition
        )
        
        if metadata:
            workflow.metadata = metadata
        
        self.workflows[workflow.workflow_id] = workflow
        self._persist_workflow(workflow)
        self._log_workflow_event(workflow.workflow_id, 'created', {'template_id': template_id})
        logger.info(f"Created workflow from template: {workflow.workflow_id}")

        return workflow
    
    def execute_workflow(self, workflow_id: str) -> bool:
        """Execute a workflow"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        workflow = self.workflows[workflow_id]
        
        if workflow.status != WorkflowStatus.PENDING:
            logger.warning(f"Workflow {workflow_id} already started")
            return False
        
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.utcnow()
        self._persist_workflow(workflow)
        self._log_workflow_event(workflow_id, 'started')

        logger.info(f"Starting workflow: {workflow.name}")
        
        try:
            for i, step in enumerate(workflow.steps):
                workflow.current_step_index = i
                
                # Check if approval required
                if step.requires_approval:
                    workflow.status = WorkflowStatus.WAITING_APPROVAL
                    self._persist_workflow(workflow)
                    self._log_workflow_event(workflow_id, 'waiting_approval', {'step_index': i})
                    logger.info(f"Workflow {workflow_id} waiting for approval at step {i}")
                    return False  # Pause execution
                
                # Execute step
                success = self._execute_step(workflow, step)
                self._persist_workflow(workflow)

                if not success:
                    workflow.status = WorkflowStatus.FAILED
                    self._persist_workflow(workflow)
                    self._log_workflow_event(workflow_id, 'failed', {'step_index': i, 'error': step.error})
                    logger.error(f"Workflow {workflow_id} failed at step {i}")
                    return False

            # All steps completed
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.utcnow()
            self._persist_workflow(workflow)
            self._log_workflow_event(workflow_id, 'completed')
            logger.info(f"Workflow {workflow.name} completed successfully")
            return True

        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            self._persist_workflow(workflow)
            self._log_workflow_event(workflow_id, 'failed', {'error': str(e)})
            logger.error(f"Workflow {workflow_id} failed with exception: {e}", exc_info=True)
            return False
    
    def approve_workflow(self, workflow_id: str, approved_by: str = "admin") -> bool:
        """Approve a workflow waiting for approval"""
        if workflow_id not in self.workflows:
            return False
        
        workflow = self.workflows[workflow_id]
        
        if workflow.status != WorkflowStatus.WAITING_APPROVAL:
            logger.warning(f"Workflow {workflow_id} not waiting for approval")
            return False
        
        workflow.status = WorkflowStatus.APPROVED
        workflow.metadata['approved_by'] = approved_by
        workflow.metadata['approved_at'] = datetime.utcnow().isoformat()
        self._persist_workflow(workflow)
        self._log_workflow_event(workflow_id, 'approved', {'approved_by': approved_by})

        logger.info(f"Workflow {workflow_id} approved by {approved_by}")

        # Resume execution
        workflow.status = WorkflowStatus.RUNNING
        self._persist_workflow(workflow)
        return self._continue_execution(workflow)
    
    def _continue_execution(self, workflow: Workflow) -> bool:
        """Continue workflow execution after approval"""
        try:
            for i in range(workflow.current_step_index, len(workflow.steps)):
                step = workflow.steps[i]
                workflow.current_step_index = i
                
                if step.requires_approval and step.status == WorkflowStatus.PENDING:
                    # Skip already approved step
                    step.status = WorkflowStatus.APPROVED
                
                success = self._execute_step(workflow, step)
                self._persist_workflow(workflow)

                if not success:
                    workflow.status = WorkflowStatus.FAILED
                    self._persist_workflow(workflow)
                    return False

                # Check for next approval gate
                if i + 1 < len(workflow.steps) and workflow.steps[i + 1].requires_approval:
                    workflow.status = WorkflowStatus.WAITING_APPROVAL
                    workflow.current_step_index = i + 1
                    self._persist_workflow(workflow)
                    return False

            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.utcnow()
            self._persist_workflow(workflow)
            return True

        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            self._persist_workflow(workflow)
            logger.error(f"Workflow continuation failed: {e}", exc_info=True)
            return False
    
    def _execute_step(self, workflow: Workflow, step: WorkflowStep) -> bool:
        """Execute a single workflow step"""
        step.status = WorkflowStatus.RUNNING
        step.started_at = datetime.utcnow()
        
        logger.info(f"Executing step: {step.action}")
        
        try:
            handler = self.action_handlers.get(step.action)
            
            if not handler:
                raise ValueError(f"Unknown action: {step.action}")
            
            result = handler(step.params)
            
            step.result = result
            step.status = WorkflowStatus.COMPLETED
            step.completed_at = datetime.utcnow()
            
            return True
        
        except Exception as e:
            step.error = str(e)
            step.status = WorkflowStatus.FAILED
            step.completed_at = datetime.utcnow()
            logger.error(f"Step {step.action} failed: {e}", exc_info=True)
            return False
    
    # Built-in action handlers
    
    def _action_log(self, params: Dict) -> Dict:
        """Log action"""
        message = params.get('message', 'No message')
        level = params.get('level', 'INFO')
        
        if level == 'ERROR':
            logger.error(message)
        elif level == 'WARNING':
            logger.warning(message)
        else:
            logger.info(message)
        
        return {'logged': True, 'message': message}
    
    def _action_http_request(self, params: Dict) -> Dict:
        """HTTP request action"""
        # Placeholder - would use requests library
        url = params.get('url')
        method = params.get('method', 'GET')
        
        logger.info(f"HTTP {method} to {url}")
        
        return {'success': True, 'url': url, 'method': method}
    
    def _action_execute_command(self, params: Dict) -> Dict:
        """Execute command action"""
        command = params.get('command')
        
        logger.info(f"Would execute command: {command}")
        
        # In production, use subprocess with safety checks
        return {'success': True, 'command': command}
    
    def _action_send_notification(self, params: Dict) -> Dict:
        """Send notification action"""
        channel = params.get('channel', 'default')
        message = params.get('message')
        
        logger.info(f"Notification to {channel}: {message}")
        
        return {'success': True, 'channel': channel}
    
    def _action_restart_service(self, params: Dict) -> Dict:
        """Restart service action"""
        service = params.get('service')
        
        logger.info(f"Restarting service: {service}")
        
        return {'success': True, 'service': service, 'restarted': True}
    
    def _action_scale_service(self, params: Dict) -> Dict:
        """Scale service action"""
        service = params.get('service')
        replicas = params.get('replicas', 1)
        
        logger.info(f"Scaling {service} to {replicas} replicas")
        
        return {'success': True, 'service': service, 'replicas': replicas}
    
    def get_workflow_status(self, workflow_id: str) -> Dict:
        """Get workflow status"""
        if workflow_id not in self.workflows:
            return None
        
        return self.workflows[workflow_id].to_dict()
    
    def list_workflows(self, status: WorkflowStatus = None) -> List[Dict]:
        """List all workflows"""
        workflows = list(self.workflows.values())
        
        if status:
            workflows = [w for w in workflows if w.status == status]
        
        return [w.to_dict() for w in workflows]
