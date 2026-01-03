const API_URL = '/api/v1';

class AdminApp {
    constructor() {
        this.token = localStorage.getItem('admin_token');
        this.users = [];
        this.nodes = [];
        this.regions = [];
        this.auditLogs = [];
        this.init();
    }

    init() {
        if (!this.token) {
            document.getElementById('login-overlay').classList.remove('hidden');
        } else {
            document.getElementById('login-overlay').classList.add('hidden');
            this.refreshAll();
        }
    }

    async refreshAll() {
        await Promise.all([
            this.fetchRegions(),
            this.fetchUsers(),
            this.fetchNodes(),
            this.fetchAuditLogs()
        ]);
        this.updateOverviewStats();
        this.renderAll();
    }

    // AUTH
    async login() {
        const u = document.getElementById('login-username').value;
        const p = document.getElementById('login-password').value;
        const formData = new URLSearchParams();
        formData.append('username', u);
        formData.append('password', p);

        try {
            const resp = await fetch(`${API_URL}/auth/login`, {
                method: 'POST',
                body: formData
            });
            const data = await resp.json();
            if (resp.ok) {
                this.token = data.access_token;
                localStorage.setItem('admin_token', this.token);
                document.getElementById('login-overlay').classList.add('hidden');
                this.refreshAll();
            } else {
                alert('Error: ' + data.detail);
            }
        } catch (e) {
            alert('Error conectando con la API');
        }
    }

    logout() {
        localStorage.removeItem('admin_token');
        window.location.reload();
    }

    // FETCHING
    async apiCall(endpoint, method = 'GET', body = null) {
        const headers = { 'Authorization': `Bearer ${this.token}` };
        if (body) headers['Content-Type'] = 'application/json';

        const resp = await fetch(`${API_URL}${endpoint}`, {
            method,
            headers,
            body: body ? JSON.stringify(body) : null
        });
        if (resp.status === 403) this.logout();
        return resp.ok ? await resp.json() : null;
    }

    async fetchUsers() { this.users = await this.apiCall('/admin/users') || []; }
    async fetchNodes() { this.nodes = await this.apiCall('/admin/nodes') || []; }
    async fetchRegions() { this.regions = await this.apiCall('/admin/regions') || []; }
    async fetchAuditLogs() { this.auditLogs = await this.apiCall('/admin/audit-logs') || []; }

    // RENDER
    renderAll() {
        this.renderUsers();
        this.renderNodes();
        this.renderRegions();
        this.renderAudit();
        this.renderRegionDropdowns();
        lucide.createIcons();
    }

    updateOverviewStats() {
        document.getElementById('stat-users').innerText = this.users.length;
        document.getElementById('stat-nodes').innerText = this.nodes.length;
        document.getElementById('stat-regions').innerText = this.regions.length;

        const recentAudit = this.auditLogs.slice(0, 5);
        let html = '';
        recentAudit.forEach(log => {
            html += `<tr class="border-b border-slate-800 hover:bg-slate-800/30">
                <td class="p-4 font-bold text-blue-400">${log.action}</td>
                <td class="p-4">${log.user_id ? log.user_id.slice(0, 8) : 'System'}</td>
                <td class="p-4 text-slate-400">${log.details}</td>
                <td class="p-4 text-xs">${new Date(log.created_at).toLocaleString()}</td>
            </tr>`;
        });
        document.getElementById('overview-audit-table').innerHTML = html;
    }

    renderUsers() {
        let html = '';
        this.users.forEach(u => {
            html += `<tr class="border-b border-slate-800">
                <td class="p-4 font-bold">${u.username}</td>
                <td class="p-4"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${u.role === 'ADMIN' ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30' : 'bg-slate-700/30 text-slate-400'}">${u.role}</span></td>
                <td class="p-4 text-xs text-slate-400">${u.device_id || '---'}</td>
                <td class="p-4 font-mono text-emerald-400">${u.assigned_ip || '---'}</td>
                <td class="p-4">${u.preferred_region_id ? 'Global/Set' : 'Opcional'}</td>
                <td class="p-4"><span class="px-2 py-1 ${u.is_active ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-500'} rounded text-xs">${u.is_active ? 'Activo' : 'Inactivo'}</span></td>
                <td class="p-4 flex gap-2">
                    <button onclick="adminApp.toggleUserStatus('${u.id}')" title="${u.is_active ? 'Desactivar' : 'Activar'}" class="p-2 hover:bg-slate-700 rounded text-${u.is_active ? 'amber-400' : 'emerald-400'}"><i data-lucide="${u.is_active ? 'user-minus' : 'user-check'}" size="16"></i></button>
                    <button onclick="adminApp.resetDevice('${u.id}')" title="Reset Device Lock" class="p-2 hover:bg-slate-700 rounded"><i data-lucide="smartphone-nfc" size="16"></i></button>
                    <button onclick="adminApp.deleteUser('${u.id}')" title="Eliminar Usuario" class="p-2 hover:bg-red-500/10 text-red-400 rounded"><i data-lucide="trash-2" size="16"></i></button>
                </td>
            </tr>`;
        });
        document.getElementById('users-table-body').innerHTML = html;
    }

    renderNodes() {
        let html = '';
        this.nodes.forEach(n => {
            const region = this.regions.find(r => r.id === n.region_id);
            html += `<div class="glass p-6 rounded-2xl border-t-4 ${n.status === 'UP' ? 'border-emerald-500' : 'border-red-500'}">
                <div class="flex justify-between items-start mb-4">
                    <div>
                        <h4 class="font-bold text-xl">${n.name}</h4>
                        <p class="text-xs text-slate-400">${region ? region.name : 'Unknown'}</p>
                    </div>
                    <span class="px-3 py-1 bg-slate-800 rounded-full text-[10px] font-bold">${n.endpoint_host}:${n.endpoint_port}</span>
                </div>
                <div class="space-y-4 mb-6">
                    <div class="space-y-1">
                        <div class="flex justify-between text-xs">
                            <span class="text-slate-500">Carga del Servidor</span>
                            <span>${n.current_peers} / ${n.max_capacity}</span>
                        </div>
                        <div class="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                            <div class="bg-blue-500 h-full rounded-full transition-all duration-500" style="width: ${(n.current_peers / n.max_capacity) * 100}%"></div>
                        </div>
                    </div>
                    <div class="grid grid-cols-2 gap-2 text-[11px] text-slate-300">
                        <div class="flex items-center gap-2 bg-slate-800/50 p-2 rounded-lg"><i data-lucide="shield" size="12" class="text-blue-400"></i> ${n.interface_name}</div>
                        <div class="flex items-center gap-2 bg-slate-800/50 p-2 rounded-lg"><i data-lucide="globe" size="12" class="text-amber-400"></i> ${n.allowed_ips.slice(0, 15)}...</div>
                        <div class="flex items-center gap-2 bg-slate-800/50 p-2 rounded-lg"><i data-lucide="map-pin" size="12" class="text-emerald-400"></i> ${n.ipv4_pool_cidr}</div>
                    </div>
                </div>
                <div class="flex justify-end gap-2 border-t border-slate-800 pt-4">
                    <button onclick="adminApp.openEditNodeModal('${n.id}')" class="flex-1 flex justify-center items-center gap-2 text-blue-400 hover:bg-blue-400/10 p-2 rounded-xl transition"><i data-lucide="edit-3" size="14"></i> Editar</button>
                    <button onclick="adminApp.deleteNode('${n.id}')" class="flex justify-center items-center text-red-400 hover:bg-red-400/10 p-2 rounded-xl transition"><i data-lucide="trash-2" size="14"></i></button>
                </div>
            </div>`;
        });
        document.getElementById('nodes-grid').innerHTML = html || '<p class="col-span-full text-center py-12 text-slate-500 italic">No hay nodos configurados</p>';
    }

    renderRegions() {
        let html = '';
        this.regions.forEach(r => {
            const nodeCount = this.nodes.filter(n => n.region_id === r.id).length;
            html += `<tr class="border-b border-slate-800 hover:bg-slate-800/30">
                <td class="p-4 font-mono text-blue-400">${r.code}</td>
                <td class="p-4">${r.name}</td>
                <td class="p-4 text-center font-bold text-slate-300">${nodeCount}</td>
                <td class="p-4">
                    <span class="px-2 py-1 ${r.is_active ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-500'} rounded text-[10px] uppercase font-bold">
                        ${r.is_active ? 'Online' : 'Offline'}
                    </span>
                </td>
                <td class="p-4">
                    <button onclick="adminApp.deleteRegion('${r.id}')" title="Eliminar Región" class="p-2 hover:bg-red-500/10 text-red-400 rounded transition">
                        <i data-lucide="trash-2" size="16"></i>
                    </button>
                </td>
            </tr>`;
        });
        document.getElementById('regions-table-body').innerHTML = html || '<tr><td colspan="5" class="p-8 text-center text-slate-500 italic">No hay regiones configuradas.</td></tr>';
    }

    async deleteNode(nodeId) {
        if (confirm('¿Estás seguro de eliminar este nodo? Los usuarios conectados a él perderán la conexión.')) {
            const res = await this.apiCall(`/admin/nodes/${nodeId}`, 'DELETE');
            if (res) {
                this.refreshAll();
            }
        }
    }

    // EDIT NODE
    async openEditNodeModal(nodeId) {
        const node = this.nodes.find(n => n.id === nodeId);
        if (!node) return;

        this.currentEditingNodeId = nodeId;

        document.getElementById('edit-node-region').value = node.region_id;
        document.getElementById('edit-node-name').value = node.name;
        document.getElementById('edit-node-host').value = node.endpoint_host;
        document.getElementById('edit-node-port').value = node.endpoint_port;
        document.getElementById('edit-node-pubkey').value = node.server_public_key;
        document.getElementById('edit-node-cidr').value = node.ipv4_pool_cidr;
        document.getElementById('edit-node-interface').value = node.interface_name;
        document.getElementById('edit-node-allowedips').value = node.allowed_ips;
        document.getElementById('edit-node-mthost').value = node.mt_host;
        document.getElementById('edit-node-mtuser').value = node.mt_user;
        document.getElementById('edit-node-mtpass').value = node.mt_pass;
        document.getElementById('edit-node-mtport').value = node.mt_api_port;

        this.openModal('modal-edit-node');
    }

    async updateNode() {
        const node = {
            region_id: document.getElementById('edit-node-region').value,
            name: document.getElementById('edit-node-name').value,
            endpoint_host: document.getElementById('edit-node-host').value,
            endpoint_port: parseInt(document.getElementById('edit-node-port').value) || 51820,
            server_public_key: document.getElementById('edit-node-pubkey').value,
            ipv4_pool_cidr: document.getElementById('edit-node-cidr').value,
            interface_name: document.getElementById('edit-node-interface').value,
            allowed_ips: document.getElementById('edit-node-allowedips').value,
            mt_host: document.getElementById('edit-node-mthost').value,
            mt_user: document.getElementById('edit-node-mtuser').value,
            mt_pass: document.getElementById('edit-node-mtpass').value,
            mt_api_port: parseInt(document.getElementById('edit-node-mtport').value) || 8750
        };
        const res = await this.apiCall(`/admin/nodes/${this.currentEditingNodeId}`, 'PATCH', node);
        if (res) {
            this.closeModal('modal-edit-node');
            this.refreshAll();
        }
    }

    renderAudit() {
        let html = '';
        this.auditLogs.forEach(log => {
            html += `<tr class="border-b border-slate-800">
                <td class="p-4 text-xs font-mono">${new Date(log.created_at).toLocaleString()}</td>
                <td class="p-4 font-bold text-blue-400">${log.action}</td>
                <td class="p-4 text-slate-400">${log.details}</td>
            </tr>`;
        });
        document.getElementById('full-audit-table').innerHTML = html;
    }

    renderRegionDropdowns() {
        ['new-node-region', 'edit-node-region', 'new-user-region'].forEach(id => {
            const select = document.getElementById(id);
            if (select) {
                select.innerHTML = this.regions.map(r => `<option value="${r.id}">${r.name} (${r.code})</option>`).join('');
            }
        });
    }

    // ACTIONS
    async createUser() {
        const username = document.getElementById('new-user-name').value;
        const password = document.getElementById('new-user-pass').value;
        const role = document.getElementById('new-user-role').value;
        const res = await this.apiCall('/admin/users', 'POST', { username, password, role });
        if (res) {
            this.closeModal('modal-add-user');
            this.refreshAll();
        }
    }

    async createNode() {
        const node = {
            region_id: document.getElementById('new-node-region').value,
            name: document.getElementById('new-node-name').value,
            endpoint_host: document.getElementById('new-node-host').value,
            endpoint_port: parseInt(document.getElementById('new-node-port').value) || 51820,
            server_public_key: document.getElementById('new-node-pubkey').value,
            ipv4_pool_cidr: document.getElementById('new-node-cidr').value,
            interface_name: document.getElementById('new-node-interface').value,
            allowed_ips: document.getElementById('new-node-allowedips').value,
            mt_host: document.getElementById('new-node-mthost').value,
            mt_user: document.getElementById('new-node-mtuser').value,
            mt_pass: document.getElementById('new-node-mtpass').value,
            mt_api_port: parseInt(document.getElementById('new-node-mtport').value) || 8750
        };

        const res = await this.apiCall('/admin/nodes', 'POST', node);
        if (res) {
            this.closeModal('modal-add-node');
            this.refreshAll();
        }
    }

    async createRegion() {
        const code = document.getElementById('new-region-code').value.toUpperCase();
        const name = document.getElementById('new-region-name').value;
        const res = await this.apiCall('/admin/regions', 'POST', { code, name });
        if (res) {
            this.closeModal('modal-add-region');
            this.refreshAll();
        }
    }

    async deleteRegion(regionId) {
        if (confirm('¿Estás seguro de eliminar esta región? Solo se puede eliminar si no tiene nodos asociados.')) {
            const res = await this.apiCall(`/admin/regions/${regionId}`, 'DELETE');
            if (res) {
                this.refreshAll();
            } else {
                alert('No se pudo eliminar la región. Verifica que no tenga nodos vinculados.');
            }
        }
    }

    async resetDevice(userId) {
        if (confirm('¿Resetear bloqueo de dispositivo para este usuario?')) {
            await this.apiCall(`/admin/users/${userId}/reset-device`, 'POST');
            this.refreshAll();
        }
    }

    async toggleUserStatus(userId) {
        const res = await this.apiCall(`/admin/users/${userId}/toggle-status`, 'POST');
        if (res) {
            this.refreshAll();
        }
    }

    async deleteUser(userId) {
        if (confirm('¿Estás seguro de eliminar este usuario? Esto revocará todos sus accesos.')) {
            const res = await this.apiCall(`/admin/users/${userId}`, 'DELETE');
            if (res) {
                this.refreshAll();
            }
        }
    }

    // UI HELPERS
    showTab(tabName) {
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        document.getElementById(`tab-${tabName}`).classList.add('active');

        document.querySelectorAll('.sidebar-item').forEach(b => b.classList.remove('active'));
        document.getElementById(`tab-btn-${tabName}`).classList.add('active');
        lucide.createIcons();
    }

    openModal(id) { document.getElementById(id).classList.remove('hidden'); }
    closeModal(id) { document.getElementById(id).classList.add('hidden'); }
}

const adminApp = new AdminApp();
window.adminApp = adminApp;
