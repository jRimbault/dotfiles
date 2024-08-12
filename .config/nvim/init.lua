local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not (vim.uv or vim.loop).fs_stat(lazypath) then
    vim.fn.system(
        {"git", "clone", "--filter=blob:none", "https://github.com/folke/lazy.nvim.git", "--branch=stable", -- latest stable release
         lazypath})
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
}, opts)

-- Basic settings
vim.opt.compatible = false
vim.opt.syntax = "on"
vim.opt.termguicolors = true
vim.cmd("colorscheme onedark")
vim.cmd("hi Normal guibg=none")
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
vim.opt.wildmode = {'longest', 'list'}
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
vim.opt.statusline = "%f%m%=%l:%c - %03p%% %y %{&fileencoding?&fileencoding:&encoding} [%{&fileformat}]"
vim.cmd("hi statusline ctermbg=0 ctermfg=0")

local statusline_visible = false
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

