/* eslint-disable react/prop-types */
import ReactMarkdown from 'react-markdown'

export function LenyMarkdown({ children }) {
  return <ReactMarkdown skipHtml disallowedElements={['img']} unwrapDisallowed
    components={{ a: ({ children }) => <span>{children}</span> }}>
    {children}
  </ReactMarkdown>
}
