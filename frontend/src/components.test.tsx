import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ErrorNotice } from './components';

describe('error request ID', () => {
  it('copies the visible ID and keeps retry available', async () => {
    const copy=vi.fn().mockResolvedValue(undefined), retry=vi.fn();
    Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:copy}});
    render(<ErrorNotice error="请求失败" requestId={'a'.repeat(32)} retry={retry} />);
    expect(screen.getByText('a'.repeat(32))).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'复制请求 ID'}));
    await waitFor(()=>expect(copy).toHaveBeenCalledWith('a'.repeat(32)));
    expect(await screen.findByText('已复制')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'重试'}));
    expect(retry).toHaveBeenCalledOnce();
  });
  it('offers manual copy if clipboard access is denied', async () => {
    Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:vi.fn().mockRejectedValue(new Error('denied'))}});
    render(<ErrorNotice error="请求失败" requestId={'b'.repeat(32)} />);
    fireEvent.click(screen.getByRole('button',{name:'复制请求 ID'}));
    expect(await screen.findByText('无法自动复制，请手动选择请求 ID 复制')).toBeInTheDocument();
    expect(screen.getByText('b'.repeat(32))).toBeInTheDocument();
  });
  it('does not show a fake ID for network errors', () => {
    render(<ErrorNotice error="无法连接服务器" />);
    expect(screen.queryByRole('button',{name:'复制请求 ID'})).not.toBeInTheDocument();
  });
});
