// ==UserScript==
// @name         GitLab delete pipeline button (HubLabBot)
// @namespace    https://github.com/Potpourri
// @version      0.0.1
// @match        https://gitlab.com/*/*/pipelines
// @require      https://unpkg.com/ky@0.15.0/umd.js
// @require      https://github.com/fuzetsu/userscripts/raw/b38eabf72c20fa3cf7da84ecd2cefe0d4a2116be/wait-for-elements/wait-for-elements.js
// @inject-into  content
// @grant        GM_getValue
// @grant        GM_setValue
// @author       Nikita Belyakov "Potpourri"
// @license      MIT
// ==/UserScript==

(function() {
"use strict"

const ky_ = ky.default
const repo_path = location.pathname
	.split("/")
	.slice(1, 3)
	.join("/")

const initValue = (key, msg) => {
	if (!GM_getValue(key)) {
		let value
		while (!value)
			value = prompt(msg)
		GM_setValue(key, value)
	}
}
const $ = (s, x = document) => x.querySelector(s)
const $el = (tag, opts) => {
	const el = document.createElement(tag)
	Object.assign(el, opts)
	return el
}

const hublabbotApi = async (method, params) => {
	try {
		const base_url = GM_getValue("HUBLABBOT_BASE_URL")
			.replace(/\/$/, "")
		const resp = await ky_(`${base_url}/api/gitlab_button`, {
			method,
			searchParams: params,
			headers: {
				"X-Gitlab-Token": GM_getValue("GITLAB_SECRET")
			}
		}).json()
		return resp
	} catch (exc) {
		console.error("HubLabBot:ERROR:", exc)
		alert("HubLabBot: Fetch error, see console for detailed informations.")
	}
}

const addDeletePipelineBtn = pipelineRow => {
	let lastCol = pipelineRow.lastElementChild
	if (!lastCol.classList.contains("pipeline-actions")) {
		const pipelineActions = $el("div", {
			className: "table-section section-20 table-button-footer pipeline-actions"
		})
		const btnGroup = $el("div", {
			className: "btn-group table-action-buttons"
		})
		pipelineActions.append(btnGroup)
		pipelineRow.append(pipelineActions)
		lastCol = pipelineActions
	}
	const btn = $el("button", {
		className: "btn btn-remove fa fa-trash-o",
		onclick: async evt => {
			if (!confirm("Are you sure?"))
				return
			const pipeline_id = $("span.pipeline-id", pipelineRow)
				.textContent
				.slice(1)
			const resp = await hublabbotApi("delete", {repo_path, pipeline_id})
			console.log("HubLabBot:SUCCESS:", resp.status)
		}
	})
	lastCol.lastElementChild.append(btn)
}

const main = async () => {
	initValue("HUBLABBOT_BASE_URL", "Please enter your HubLabBot base url.")
	initValue("GITLAB_SECRET", "Please enter your GitLab secret.")
	const resp = await hublabbotApi("get", {repo_path, is_enabled: ''})
	if (resp.value)
		waitForElems({
			sel: "div.commit.gl-responsive-table-row",
			onmatch: addDeletePipelineBtn
		})
	else
		console.log(`HubLabBot:INFO: delete pipeline button disabled for ${repo_path}.`)
}

main()

})()
