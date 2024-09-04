-- always set leader first!
vim.keymap.set("n", "<Space>", "<Nop>", { silent = true })
vim.g.mapleader = " "

local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not (vim.uv or vim.loop).fs_stat(lazypath) then
    vim.fn.system({
        "git",
        "clone",
        "--filter=blob:none",
        "https://github.com/folke/lazy.nvim.git",
        "--branch=stable", -- latest stable release
         lazypath,
     })
end
vim.opt.rtp:prepend(lazypath)

local lazy = require("lazy")
lazy.setup({
    "itspriddle/vim-shellcheck",
    "navarasu/onedark.nvim",
    "fxn/vim-monochrome",
    { 'numToStr/Comment.nvim', lazy = false },
    { "nvim-treesitter/nvim-treesitter", build = ":TSUpdate" },
    {
        'nvim-telescope/telescope.nvim',
        tag = '0.1.8',
        dependencies = { 'nvim-lua/plenary.nvim' },
    },
    -- nice bar at the bottom
	{
		'itchyny/lightline.vim',
		lazy = false, -- also load at start since it's UI
		config = function()
			-- no need to also show mode in cmd line when we have bar
			vim.o.showmode = false
			vim.g.lightline = {
				active = {
					left = {
						{ 'mode', 'paste' },
						{ 'readonly', 'filename', 'modified' }
					},
					right = {
						{ 'lineinfo' },
						{ 'percent' },
						{ 'fileencoding', 'filetype' }
					},
				},
				component_function = {
					filename = 'LightlineFilename'
				},
			}
			function LightlineFilenameInLua(opts)
				if vim.fn.expand('%:t') == '' then
					return '[No Name]'
				else
					return vim.fn.getreg('%')
				end
			end
			-- https://github.com/itchyny/lightline.vim/issues/657
			vim.api.nvim_exec(
				[[
				function! g:LightlineFilename()
					return v:lua.LightlineFilenameInLua()
				endfunction
				]],
				true
			)
		end
	},
    -- LSP
    {
		'neovim/nvim-lspconfig',
		config = function()
			-- Setup language servers.
			local lspconfig = require('lspconfig')

			-- Rust
			lspconfig.rust_analyzer.setup {
				-- Server-specific settings. See `:help lspconfig-setup`
				settings = {
					["rust-analyzer"] = {
						cargo = {
							allFeatures = true,
						},
						imports = {
							group = {
								enable = false,
							},
						},
						completion = {
							postfix = {
								enable = false,
							},
						},
					},
				},
			}
            -- Python LSP
            lspconfig.pyright.setup{
                settings = {
                    ["pyright"] = {
						completion = {
							postfix = {
								enable = false,
							},
						},
                    }
                }
            }

			-- Bash LSP
			local configs = require 'lspconfig.configs'
			if not configs.bash_lsp and vim.fn.executable('bash-language-server') == 1 then
				configs.bash_lsp = {
					default_config = {
						cmd = { 'bash-language-server', 'start' },
						filetypes = { 'sh' },
						root_dir = require('lspconfig').util.find_git_ancestor,
						init_options = {
							settings = {
								args = {}
							}
						}
					}
				}
			end
			if configs.bash_lsp then
				lspconfig.bash_lsp.setup {}
			end

			-- Global mappings.
			-- See `:help vim.diagnostic.*` for documentation on any of the below functions
			vim.keymap.set('n', '<leader>e', vim.diagnostic.open_float)
			vim.keymap.set('n', '[d', vim.diagnostic.goto_prev)
			vim.keymap.set('n', ']d', vim.diagnostic.goto_next)
			vim.keymap.set('n', '<leader>q', vim.diagnostic.setloclist)

			-- Use LspAttach autocommand to only map the following keys
			-- after the language server attaches to the current buffer
			vim.api.nvim_create_autocmd('LspAttach', {
				group = vim.api.nvim_create_augroup('UserLspConfig', {}),
				callback = function(ev)
					-- Enable completion triggered by <c-x><c-o>
					vim.bo[ev.buf].omnifunc = 'v:lua.vim.lsp.omnifunc'

					-- Buffer local mappings.
					-- See `:help vim.lsp.*` for documentation on any of the below functions
					local opts = { buffer = ev.buf }
					vim.keymap.set('n', 'gD', vim.lsp.buf.declaration, opts)
					vim.keymap.set('n', 'gd', vim.lsp.buf.definition, opts)
					vim.keymap.set('n', 'K', vim.lsp.buf.hover, opts)
					vim.keymap.set('n', 'gi', vim.lsp.buf.implementation, opts)
					vim.keymap.set('n', '<C-k>', vim.lsp.buf.signature_help, opts)
					vim.keymap.set('n', '<leader>wa', vim.lsp.buf.add_workspace_folder, opts)
					vim.keymap.set('n', '<leader>wr', vim.lsp.buf.remove_workspace_folder, opts)
					vim.keymap.set('n', '<leader>wl', function()
						print(vim.inspect(vim.lsp.buf.list_workspace_folders()))
					end, opts)
					--vim.keymap.set('n', '<space>D', vim.lsp.buf.type_definition, opts)
					vim.keymap.set('n', '<leader>r', vim.lsp.buf.rename, opts)
					vim.keymap.set({ 'n', 'v' }, '<leader>a', vim.lsp.buf.code_action, opts)
					vim.keymap.set('n', 'gr', vim.lsp.buf.references, opts)
					vim.keymap.set('n', '<leader>f', function()
						vim.lsp.buf.format { async = true }
					end, opts)

					local client = vim.lsp.get_client_by_id(ev.data.client_id)

					-- When https://neovim.io/doc/user/lsp.html#lsp-inlay_hint stabilizes
					-- *and* there's some way to make it only apply to the current line.
					-- if client.server_capabilities.inlayHintProvider then
					--     vim.lsp.inlay_hint(ev.buf, true)
					-- end

					-- None of this semantics tokens business.
					-- https://www.reddit.com/r/neovim/comments/143efmd/is_it_possible_to_disable_treesitter_completely/
					client.server_capabilities.semanticTokensProvider = nil
				end,
			})
		end
	},
    -- language support
    -- toml
	'cespare/vim-toml',
    -- yaml
	{
		"cuducos/yaml.nvim",
		ft = { "yaml" },
		dependencies = {
			"nvim-treesitter/nvim-treesitter",
		},
	},
    -- rust
	{
		'rust-lang/rust.vim',
		ft = { "rust" },
		config = function()
			vim.g.rustfmt_autosave = 1
			vim.g.rustfmt_emit_files = 1
			vim.g.rustfmt_fail_silently = 0
			vim.g.rust_clip_command = 'wl-copy'
		end
	},
    -- markdown
	{
		'plasticboy/vim-markdown',
		ft = { "markdown" },
		dependencies = {
			'godlygeek/tabular',
		},
		config = function()
			-- never ever fold!
			vim.g.vim_markdown_folding_disabled = 1
			-- support front-matter in .md files
			vim.g.vim_markdown_frontmatter = 1
			-- 'o' on a list item should insert at same level
			vim.g.vim_markdown_new_list_item_indent = 0
			-- don't add bullets when wrapping:
			-- https://github.com/preservim/vim-markdown/issues/232
			vim.g.vim_markdown_auto_insert_bullets = 0
		end
	},
    -- LSP-based code-completion
	{
		"hrsh7th/nvim-cmp",
		-- load cmp on InsertEnter
		event = "InsertEnter",
		-- these dependencies will only be loaded when cmp loads
		-- dependencies are always lazy-loaded unless specified otherwise
		dependencies = {
			'neovim/nvim-lspconfig',
			"hrsh7th/cmp-nvim-lsp",
			"hrsh7th/cmp-buffer",
			"hrsh7th/cmp-path",
		},
		config = function()
			local cmp = require'cmp'
			cmp.setup({
				snippet = {
					-- REQUIRED by nvim-cmp. get rid of it once we can
					expand = function(args)
						vim.fn["vsnip#anonymous"](args.body)
					end,
				},
				mapping = cmp.mapping.preset.insert({
					['<C-b>'] = cmp.mapping.scroll_docs(-4),
					['<C-f>'] = cmp.mapping.scroll_docs(4),
					['<C-Space>'] = cmp.mapping.complete(),
					['<C-e>'] = cmp.mapping.abort(),
					-- Accept currently selected item.
					-- Set `select` to `false` to only confirm explicitly selected items.
					['<CR>'] = cmp.mapping.confirm({ select = true }),
				}),
				sources = cmp.config.sources({
					{ name = 'nvim_lsp' },
				}, {
					{ name = 'path' },
				}),
				experimental = {
					ghost_text = true,
				},
			})

			-- Enable completing paths in :
			cmp.setup.cmdline(':', {
				sources = cmp.config.sources({
					{ name = 'path' }
				})
			})
		end
	},
}, opts)

-- Basic settings
vim.opt.compatible = false
vim.opt.syntax = "on"
vim.opt.termguicolors = true
vim.cmd("colorscheme onedark")
vim.cmd("hi Normal guibg=none")
vim.opt.background = "dark"
vim.opt.guicursor = ""

-- Toggle line numbers
vim.keymap.set('n', ',l', ':set number! relativenumber!<CR>', {
    noremap = true
})

-- Toggle display of whitespace
vim.opt.listchars = {
    space = '·',
    tab = '» ',
    extends = '›',
    precedes = '‹',
    eol = '↲'
}
vim.opt.showbreak = '↪ '
vim.keymap.set('n', ',ws', ':set list!<CR>', {
    noremap = true
})

-- Smart search
vim.opt.ignorecase = true
vim.opt.smartcase = true
vim.opt.showmatch = true
vim.opt.hlsearch = true

-- Keep cursor in the middle
vim.opt.scrolloff = 8

-- Disable swap files and backups
vim.opt.backup = false
vim.opt.writebackup = false
vim.opt.backupdir = "/tmp"
vim.opt.directory = "/tmp"

-- Limit to 80 columns
vim.opt.winwidth = 79
vim.opt.shiftwidth = 4
vim.opt.tabstop = 4
vim.opt.expandtab = true
vim.opt.softtabstop = 4
vim.opt.shiftround = true
vim.opt.autoindent = true
vim.opt.smartindent = true
vim.opt.cindent = false

-- Allow backspacing over everything in insert mode
vim.opt.backspace = {'indent', 'eol', 'start'}

-- Highlight current line
vim.opt.cmdheight = 1
vim.opt.switchbuf = "useopen"
vim.keymap.set('n', ',hl', ':set cursorline!<CR>', {
    noremap = true
})

-- Emacs-style tab completion when selecting files
vim.opt.wildmode = "list:longest"
vim.opt.wildmenu = true

-- Load indent files for language-dependent indenting
vim.cmd("filetype plugin indent on")

-- Automatically reload files changed outside of vim
vim.opt.autoread = true

-- Trim trailing whitespace on save
vim.api.nvim_create_autocmd("BufWritePre", {
    pattern = "*",
    command = [[%s/\s\+$//e]]
})

-- Autocommands for specific file types and cases
vim.api.nvim_create_augroup("vimrcEx", {
    clear = true
})
vim.api.nvim_create_autocmd("FileType", {
    group = "vimrcEx",
    pattern = {"cucumber", "eruby", "haml", "html", "javascript", "ruby", "sass", "yaml"},
    command = "set ai sw=2 sts=2 et"
})
vim.api.nvim_create_autocmd("FileType", {
    group = "vimrcEx",
    pattern = {"c", "cpp", "h", "php", "python", "rust"},
    command = "set ai sw=4 sts=4 et"
})
vim.api.nvim_create_autocmd("FileType", {
    group = "vimrcEx",
    pattern = "*.md",
    command = "setlocal ft="
})
vim.api.nvim_create_autocmd("CmdwinEnter", {
    group = "vimrcEx",
    command = "unmap <CR>"
})
vim.api.nvim_create_autocmd("CmdwinLeave", {
    group = "vimrcEx",
    command = "call MapCR()"
})

-- Remove fancy characters command
local function remove_fancy_characters()
    local typo = {
        ["“"] = '"',
        ["”"] = '"',
        ["‘"] = "'",
        ["’"] = "'",
        ["–"] = '--',
        ["—"] = '---',
        ["…"] = '...'
    }
    for k, v in pairs(typo) do
        vim.cmd(string.format("%%s/%s/%s/g", k, v))
    end
end
vim.api.nvim_create_user_command("RemoveFancyCharacters", remove_fancy_characters, {})

-- Pair programming: Insert a Co-authored-by line in commit message
local function commit_coauthored_by()
    vim.cmd([[read !echo "Co-authored-by: $(git authors | fzf)"]])
end
vim.api.nvim_create_user_command("CommitCoAuthoredBy", commit_coauthored_by, {})

-- Status line configuration
-- vim.opt.statusline = "%f%m%=%l:%c - %03p%% %y %{&fileencoding?&fileencoding:&encoding} [%{&fileformat}]"
-- vim.cmd("hi statusline ctermbg=0 ctermfg=0")

local statusline_visible = true
local function toggle_statusline()
    statusline_visible = not statusline_visible
    vim.opt.laststatus = statusline_visible and 2 or 0
end
vim.opt.laststatus = statusline_visible and 2 or 0
vim.keymap.set('n', ',ts', toggle_statusline, {
    noremap = true
})

local ruler_visible = false
local function toggle_ruler()
    ruler_visible = not ruler_visible
    vim.opt.colorcolumn = ruler_visible and "80" or "0"
end
vim.keymap.set('n', ',tr', toggle_ruler, {
    noremap = true
})

local function toggle_all()
    vim.cmd("set number! relativenumber!")
    toggle_statusline()
    vim.cmd("set cursorline!")
end
vim.keymap.set('n', ',ta', toggle_all, {
    noremap = true
})

-- Run current file
local function run_file()
    if vim.fn.expand("%") ~= "" then
        vim.cmd("w")
    end
    if vim.fn.executable(vim.fn.expand("%")) == 1 then
        vim.cmd("!" .. vim.fn.expand("%"))
    end
end
vim.keymap.set('n', '<space><space>', run_file, {
    noremap = true
})

-- Source local config
vim.g.loaded_matchparen = 1
vim.cmd("runtime! lvimrc")

-- Plugin setups
require('Comment').setup()

local builtin = require('telescope.builtin')
vim.keymap.set('n', ',ff', builtin.find_files, {})
vim.keymap.set('n', ',fg', builtin.live_grep, {})
vim.keymap.set('n', ',fb', builtin.buffers, {})
vim.keymap.set('n', ',fh', builtin.help_tags, {})

