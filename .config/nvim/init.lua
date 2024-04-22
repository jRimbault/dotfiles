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

require("lazy").setup({
    "joshdick/onedark.vim",
    "fxn/vim-monochrome",
}, opts)

vim.cmd([[
  " remove all autocmds in the global space
  autocmd!

  " Basic stuff
  set nocompatible
  syntax on
  set termguicolors
  colorscheme monochrome
  set guicursor=

  " Toggle display of line numbers
  function! ToggleLineNumbers()
    set number!
    set relativenumber!
  endfunction
  nnoremap ,l :call ToggleLineNumbers() <cr>

  " Toggle display of whitespace
  let &showbreak='↪ '
  set listchars=space:·,tab:»\ ,extends:›,precedes:‹,eol:↲
  function! ToggleWhiteSpace()
    set list!
  endfunction
  nnoremap ,ws :call ToggleWhiteSpace() <cr>

  " Set colorscheme for git commit editing :
  " autocmd BufRead COMMIT_EDITMSG colorscheme white

  " Smart search
  set ignorecase smartcase
  set showmatch
  set hlsearch

  " keep cursor in the middle
  set scrolloff=8

  " Swap files and no backups (don't)
  set nobackup
  set nowritebackup
  set backupdir=/tmp
  set directory=/tmp

  " Limit to 80 columns
  set winwidth=79
  set textwidth=79
  " Spaces are the way
  set shiftwidth=4
  set tabstop=4
  set expandtab
  set softtabstop=4
  set shiftround
  " Default indentation
  set autoindent
  set smartindent
  set nocindent

  " allow backspacing over everything in insert mode
  set backspace=indent,eol,start

  " highlight current line
  set cmdheight=1
  set switchbuf=useopen
  function! HighlightCurrentLine()
    set cursorline!
  endfunction
  nnoremap ,hl :call HighlightCurrentLine() <cr>

  " use emacs-style tab completion when selecting files, etc
  set wildmode=longest,list
  " make tab completion for files/buffers act like bash
  set wildmenu

  " load indent files, to automatically do language-dependent indenting.
  filetype plugin indent on

  " If a file is changed outside of vim, automatically reload it without asking
  set autoread

  " Trim trailing whitespace
  autocmd BufWritePre * %s/\s\+$//e
  augroup vimrcEx
    " Clear all autocmds in the group
    autocmd!

    " for javascript, autoindent with two spaces, always expand tabs
    autocmd FileType javascript,ruby,haml,eruby,yaml,html,sass,cucumber, set ai sw=2 sts=2 et
    " for python, autoindent with four spaces, always expand tabs
    autocmd FileType python,c,cpp,h,php set ai sw=4 sts=4 et

    autocmd! BufRead,BufNewFile *.sass setfiletype sass

    " Don't syntax highlight markdown because it's often wrong
    autocmd! FileType mkd setlocal syn=off
    autocmd BufRead *.mkd  set ai formatoptions=tcroqn2 comments=n:&gt;
    autocmd BufRead *.markdown  set ai formatoptions=tcroqn2 comments=n:&gt;
    " *.md is markdown
    autocmd! BufNewFile,BufRead *.md setlocal ft=

    " Leave the return key alone when in command line windows, since it's used
    " to run commands there.
    autocmd! CmdwinEnter * :unmap <cr>
    autocmd! CmdwinLeave * :call MapCR()
  augroup END

  " RemoveFancyCharacters COMMAND
  " Remove smart quotes, etc.
  function! RemoveFancyCharacters()
    let typo = {
      \ "“": '"',
      \ "”": '"',
      \ "‘": "'",
      \ "’": "'",
      \ "–": '--',
      \ "—": '---',
      \ "…": '...',
      \}
    :exe ":%s/".join(keys(typo), '\|').'/\=typo[submatch(0)]/ge'
  endfunction
  command! RemoveFancyCharacters :call RemoveFancyCharacters()

  " When pair programming
  " Insert a remark about that in the commit message
  " The list will only be composed of previous committer to the current repo
  function! CommitCoAuthoredBy()
    read! echo "Co-authored-by: $(git authors | fzf)"
  endfunction
  command! CommitCoAuthoredBy :call CommitCoAuthoredBy()

  " MULTIPURPOSE TAB KEY
  " Indent if we're at the beginning of a line. Else, do completion (current buffer).
  function! InsertTabWrapper()
    let col = col('.') - 1
    if !col || getline('.')[col - 1] !~ '\k'
        return "\<tab>"
    else
        return "\<c-p>"
    endif
  endfunction
  inoremap <expr> <tab> InsertTabWrapper()
  inoremap <s-tab> <c-n>

  " Status Line Stuff (CAPITAL S STUFF)
  set statusline=%f
  set statusline+=%m
  " separator
  set statusline+=%=
  set statusline+=\ %l:%c
  set statusline+=\ -
  set statusline+=\ %03p%%
  set statusline+=\ %y
  set statusline+=\ %{&fileencoding?&fileencoding:&encoding}
  set statusline+=\ [%{&fileformat}\]
  set statusline+=\ " padding space

  hi statusline ctermbg=0 ctermfg=0

  let s:hidden_statusline=0
  function! ToggleStatusLine()
    if s:hidden_statusline == 0
        let s:hidden_statusline=1
        set laststatus=2
    else
        let s:hidden_statusline=0
        set laststatus=0
    endif
  endfunction
  nnoremap ,ts :call ToggleStatusLine() <cr>

  set laststatus=0

  let s:ruler=0
  function! ToggleRuler()
    if s:ruler == 0
        set colorcolumn=80
        let s:ruler=1
    else
        set colorcolumn=0
        let s:ruler=0
    endif
  endfunction
  nnoremap ,tr :call ToggleRuler() <cr>

  function! ToggleAll()
    call ToggleLineNumbers()
    call ToggleStatusLine()
    call ToggleWhiteSpace()
    call HighlightCurrentLine()
  endfunction
  nnoremap ,ta :call ToggleAll() <cr>

  "" insert closing character when typing the opening character
  " inoremap { {}<esc>i
  " inoremap ( ()<esc>i
  " inoremap [ []<esc>i
  " inoremap " ""<esc>i
  " inoremap ' ''<esc>i

  " run current file
  function! RunFile(filename)
    if expand("%") != ""
        :w
    end
    if executable(a:filename)
        exec ":!" . a:filename
    end
  endfunction
  nnoremap <space><space> :call RunFile(expand("%"))<cr>

  " source local config
  let loaded_matchparen = 1
  runtime lvimrc
]])
